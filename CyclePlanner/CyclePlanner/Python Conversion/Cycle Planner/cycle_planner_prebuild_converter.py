"""
CyclePlannerPrebuild Converter
Master consolidation of all CyclePlanner data sources
Replaces CyclePlannerPrebuild.pq
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    export_with_fallback,
    ensure_export_folder
)

TIME_PHASE_WEEKS = 20
FORECAST_SY_TO_LF_FACTOR = 9 / 12
FORECAST_LF_TO_SY_FACTOR = 12 / 9


def position_to_week(value, weeks: int = TIME_PHASE_WEEKS) -> int:
    """Convert a position value to a bounded week number."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric) or numeric <= 0:
        return 1
    return max(1, min(int(numeric), weeks))

def calculate_time_phased_inventory(on_hand, forecast_row, production_row, shipments_row):
    """
    Calculate cumulative inventory projection for weeks 1-20
    
    Formula for each week: Inventory = Previous_Inventory - Forecast + Production - Shipments
    
    This replaces the Power Query fnTimePhasedInventory function with vectorized operations
    """
    weeks = range(1, TIME_PHASE_WEEKS + 1)
    
    # Extract values for each week (default to 0 if missing)
    fc_values = [forecast_row.get(f'FC W {i:02d}', 0) if forecast_row is not None else 0 for i in weeks]
    pd_values = [production_row.get(f'PD W {i:02d}', 0) if production_row is not None else 0 for i in weeks]
    sh_values = [shipments_row.get(f'SH W {i:02d}', 0) if shipments_row is not None else 0 for i in weeks]
    
    # Convert to numpy arrays for vectorized calculation
    fc_array = np.array(fc_values, dtype=float)
    pd_array = np.array(pd_values, dtype=float)
    sh_array = np.array(sh_values, dtype=float)
    
    # Calculate net change per week: -forecast + production - shipments
    net_change = -fc_array + pd_array - sh_array
    
    # Calculate cumulative inventory (starting with on_hand)
    cumulative = np.zeros(TIME_PHASE_WEEKS)
    cumulative[0] = on_hand + net_change[0]
    for i in range(1, TIME_PHASE_WEEKS):
        cumulative[i] = cumulative[i-1] + net_change[i]
    
    # Return as dictionary
    return {f'Week {i:02d}': cumulative[i-1] for i in weeks}

def load_all_data(export_folder: Path) -> dict:
    """Load all CSV files from previous phases"""
    files = {
        'product_specs': 'product_specs.csv',
        'inventory': 'inventory.csv',
        'sales_forecast': 'sales_forecast.csv',
        'mill_orders': 'mill_orders.csv',
        'production_orders': 'production_orders.csv',
        'time_phase_production': 'time_phase_production_orders.csv',
        'time_phase_shipments': 'time_phase_shipments.csv'
    }
    
    # Force key columns to load as strings to preserve leading zeros
    dtype_dict = {
        'Style': 'string', 'Color': 'string', 'Size': 'string', 'Back': 'string',
        'PGSTYL': 'string', 'PGCLR': 'string', 'PGSIZE': 'string', 'PGBACK': 'string'
    }
    
    data = {}
    for key, filename in files.items():
        filepath = export_folder / filename
        if filepath.exists():
            data[key] = pd.read_csv(filepath, dtype=dtype_dict)
            print(f"  Loaded {key}: {len(data[key])} rows")
        else:
            print(f"  ⚠ {key} not found at {filepath}")
            data[key] = pd.DataFrame()
    
    return data

def clean_key_value(value):
    """Convert keys to clean strings: trim whitespace, remove .0 suffixes."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def coerce_numeric_series(series: pd.Series) -> pd.Series:
    """Coerce numeric values, stripping thousands separators when present."""
    if series.empty:
        return series
    return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")


def normalize_join_keys(data: dict) -> dict:
    """
    Normalize join key columns to consistent data types across all datasets
    Ensures Style, Color, Size, Back are all strings (trim whitespace, remove .0 suffixes)
    """
    join_keys = ['Style', 'Color', 'Size', 'Back', 'PGSTYL', 'PGCLR', 'PGSIZE', 'PGBACK']

    for key, df in data.items():
        if df.empty:
            continue
        for col in join_keys:
            if col in df.columns:
                df[col] = df[col].map(clean_key_value).astype('string')
    
    return data

def apply_planning_groups(df: pd.DataFrame, planning_groups_df: pd.DataFrame) -> pd.DataFrame:
    """Fill PlanningGroup and ColorGroup from Planning_Groups Excel data."""
    if df.empty or planning_groups_df.empty:
        return df

    join_keys = ['Style', 'Color', 'Size', 'Back']
    pg_cols = join_keys + ['PlanGroup', 'ColorGroup']
    pg_subset = planning_groups_df[[c for c in pg_cols if c in planning_groups_df.columns]].copy()

    merged = df.merge(pg_subset, on=join_keys, how='left', suffixes=('', '_pg'))
    if 'PlanningGroup' not in merged.columns and 'PlanGroup' in merged.columns:
        merged['PlanningGroup'] = merged['PlanGroup']
    if 'PlanningGroup' in merged.columns and 'PlanGroup_pg' in merged.columns:
        merged['PlanningGroup'] = merged['PlanningGroup'].fillna(merged['PlanGroup_pg'])
    if 'ColorGroup' in merged.columns and 'ColorGroup_pg' in merged.columns:
        merged['ColorGroup'] = merged['ColorGroup'].fillna(merged['ColorGroup_pg'])
    if 'ColorGroup' not in merged.columns and 'ColorGroup_pg' in merged.columns:
        merged['ColorGroup'] = merged['ColorGroup_pg']

    drop_cols = [col for col in ['PlanGroup', 'PlanGroup_pg', 'ColorGroup_pg'] if col in merged.columns]
    if drop_cols:
        merged = merged.drop(columns=drop_cols)

    return merged

def build_master_dataset(data: dict, planning_groups_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the master CyclePlanner dataset by joining all sources
    """
    # Start with Product_Specs as the base
    result = data['product_specs'].copy()
    print(f"\nStarting with Product_Specs: {len(result)} rows")
    
    # Join keys
    join_keys = ['Style', 'Color', 'Size', 'Back']
    
    # 1. Calculate AsgQty and ReservedQty from MillOrderProductionAssignment
    mill_orders_pa = data['mill_orders'][data['mill_orders']['Src'] == 'Production Assignment'].copy()
    if not mill_orders_pa.empty:
        asg_summary = mill_orders_pa.groupby(join_keys).agg({
            'PendingProd': 'sum',
            'RsvQty': 'sum'
        }).reset_index()
        asg_summary.rename(columns={'PendingProd': 'AsgQty LF', 'RsvQty': 'ReservedQty LF'}, inplace=True)
        result = result.merge(asg_summary, on=join_keys, how='left')
        print(f"  + Added AsgQty LF and ReservedQty LF")
    else:
        result['AsgQty LF'] = 0
        result['ReservedQty LF'] = 0
    
    # 2. Calculate B/O from UnassignedMillOrders
    unassigned = data['mill_orders'][data['mill_orders']['Src'] == 'Unassigned'].copy()
    if not unassigned.empty:
        # If UOM='RL', multiply by RollSize; otherwise use Qty as-is
        # Need to merge with product_specs to get RollSize
        unassigned = unassigned.merge(
            result[join_keys + ['RollSize']], 
            on=join_keys, 
            how='left'
        )
        unassigned['Calc'] = unassigned.apply(
            lambda row: row['Qty'] * row['RollSize'] if row['UOM'] == 'RL' else row['Qty'],
            axis=1
        )
        bo_summary = unassigned.groupby(join_keys)['Calc'].sum().reset_index()
        bo_summary.rename(columns={'Calc': 'B/O LF'}, inplace=True)
        max_bo_summary = unassigned.groupby(join_keys)['Calc'].max().reset_index()
        max_bo_summary.rename(columns={'Calc': 'Max BO Order LF'}, inplace=True)
        result = result.merge(bo_summary, on=join_keys, how='left')
        result = result.merge(max_bo_summary, on=join_keys, how='left')
        print(f"  + Added B/O LF and Max BO Order LF")
    else:
        result['B/O LF'] = 0
        result['Max BO Order LF'] = 0
    
    # 3. Calculate Inv LF from Inventory
    if not data['inventory'].empty:
        # Use BalFeet as the inventory column
        feet_col = 'BalFeet'
        if feet_col not in data['inventory'].columns:
            print(f"  ⚠ Warning: 'BalFeet' not found in inventory")
            print(f"    Available columns: {data['inventory'].columns.tolist()}")
            result['Inv LF'] = 0
        else:
            # Compute both total (Inv LF) and largest single roll (Max Roll LF) in one pass
            inventory_agg = data['inventory'].groupby(join_keys)[feet_col].agg(['sum', 'max']).reset_index()
            inventory_agg.columns = join_keys + ['Inv LF', 'Max Roll LF']
            result = result.merge(inventory_agg, on=join_keys, how='left')
            print(f"  + Added Inv LF and Max Roll LF")
    else:
        result['Inv LF'] = 0
        result['Max Roll LF'] = 0
    
    # Replace null values with 0
    result['Inv LF'] = result['Inv LF'].fillna(0)
    result['Max Roll LF'] = result['Max Roll LF'].fillna(0)
    
    # 4. Merge Sales Forecast (keep all week columns)
    if not data['sales_forecast'].empty:
        # Drop any columns that might conflict (keep only join keys + FC columns)
        fc_cols = [f'FC W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
        keep_cols = join_keys + fc_cols + ['PlanGroup', 'ColorGroup']
        sf_subset = data['sales_forecast'][[c for c in keep_cols if c in data['sales_forecast'].columns]].copy()
        result = result.merge(sf_subset, on=join_keys, how='left')

        # Forecast arrives in SY/Wk; convert to LF/Wk for 12-foot-wide product assumptions.
        existing_fc_cols = [col for col in fc_cols if col in result.columns]
        for col in existing_fc_cols:
            result[col] = coerce_numeric_series(result[col]).fillna(0) * FORECAST_SY_TO_LF_FACTOR
        print(f"  + Merged Sales Forecast")

    if 'ColorGroup_x' in result.columns:
        result['ColorGroup'] = result['ColorGroup_x']
        result = result.drop(columns=[col for col in ['ColorGroup_x', 'ColorGroup_y'] if col in result.columns])
    if 'PlanningGroup' not in result.columns and 'PlanGroup' in result.columns:
        result['PlanningGroup'] = result['PlanGroup']

    # Ensure PlanningGroup/ColorGroup are fully populated from Planning_Groups
    result = apply_planning_groups(result, planning_groups_df)
    
    # 5. Merge Time-Phased Production Orders
    if not data['time_phase_production'].empty:
        # Prefer PG keys when available so x-ref production maps back to base planning SKU.
        pd_cols = [f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
        tp_df = data['time_phase_production'].copy()
        pg_join_keys = ['PGSTYL', 'PGCLR', 'PGSIZE', 'PGBACK']

        if all(col in tp_df.columns for col in pg_join_keys):
            keep_cols = pg_join_keys + pd_cols
            tp_subset = tp_df[[c for c in keep_cols if c in tp_df.columns]].copy()
            tp_subset = tp_subset.rename(columns={
                'PGSTYL': 'Style',
                'PGCLR': 'Color',
                'PGSIZE': 'Size',
                'PGBACK': 'Back'
            })
            existing_pd_cols = [col for col in pd_cols if col in tp_subset.columns]
            tp_subset = tp_subset.groupby(join_keys, as_index=False, dropna=False)[existing_pd_cols].sum()
            print("  + Time-Phase Production uses PG key mapping")
        else:
            keep_cols = join_keys + pd_cols
            tp_subset = tp_df[[c for c in keep_cols if c in tp_df.columns]].copy()

        before_merge = len(result)
        result = result.merge(tp_subset, on=join_keys, how='left', indicator='_prod_merge')
        matched = (result['_prod_merge'] == 'both').sum()
        result.drop('_prod_merge', axis=1, inplace=True)
        print(f"  + Merged Time-Phase Production ({matched}/{before_merge} rows matched)")
    
    # 6. Merge Time-Phased Shipments
    if not data['time_phase_shipments'].empty:
        # Keep only join keys + SH columns
        sh_cols = [f'SH W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
        keep_cols = join_keys + sh_cols
        ts_subset = data['time_phase_shipments'][[c for c in keep_cols if c in data['time_phase_shipments'].columns]].copy()
        before_merge = len(result)
        result = result.merge(ts_subset, on=join_keys, how='left', indicator='_ship_merge')
        matched = (result['_ship_merge'] == 'both').sum()
        result.drop('_ship_merge', axis=1, inplace=True)
        print(f"  + Merged Time-Phase Shipments ({matched}/{before_merge} rows matched)")
    
    return result

def add_time_phased_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Week 01...Week 20 columns with cumulative inventory projection
    """
    print("\nCalculating time-phased inventory...")
    
    # Prepare column lists
    fc_cols = [f'FC W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    pd_cols = [f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    sh_cols = [f'SH W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    week_cols = [f'Week {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]

    for col in ['Inv LF', 'B/O LF', 'ReservedQty LF', 'AsgQty LF', 'Open Tuft LF']:
        if col in df.columns:
            df[col] = coerce_numeric_series(df[col]).fillna(0)
    
    # Ensure all required columns exist (fill with 0 if missing)
    for col in fc_cols + pd_cols + sh_cols:
        if col not in df.columns:
            df[col] = 0
        else:
            # Fill NaN values with 0 (for rows without forecast/production/shipment data)
            df[col] = df[col].fillna(0)
            df[col] = coerce_numeric_series(df[col]).fillna(0)
    
    # Calculate time-phased inventory for each row
    time_phase_results = []
    for idx, row in df.iterrows():
        has_open_tuft = 'Open Tuft LF' in df.columns
        if has_open_tuft:
            on_hand = (
                row.get('Inv LF', 0)
                + row.get('Open Tuft LF', 0)
                - row.get('B/O LF', 0)
                - row.get('ReservedQty LF', 0)
                - row.get('AsgQty LF', 0)
            )
        else:
            on_hand = row.get('Inv LF', 0)
        
        # Get forecast, production, and shipments as dictionaries
        forecast_row = {col: row.get(col, 0) for col in fc_cols}
        if has_open_tuft:
            production_row = {col: 0 for col in pd_cols}
            shipments_row = {col: 0 for col in sh_cols}
        else:
            production_row = {col: row.get(col, 0) for col in pd_cols}
            shipments_row = {col: row.get(col, 0) for col in sh_cols}
        
        # Calculate time-phased inventory
        time_phase = calculate_time_phased_inventory(
            on_hand, 
            forecast_row, 
            production_row, 
            shipments_row
        )
        time_phase_results.append(time_phase)
    
    # Add week columns to dataframe
    time_phase_df = pd.DataFrame(time_phase_results)
    for col in week_cols:
        df[col] = time_phase_df[col]
    
    print(f"  ✓ Added {len(week_cols)} week projection columns")
    return df

def add_calculated_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add average forecast and total production metrics"""
    
    # Calculate Avg Forecast (average of FC W 01...20)
    fc_cols = [f'FC W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    existing_fc_cols = [col for col in fc_cols if col in df.columns]
    if existing_fc_cols:
        for col in existing_fc_cols:
            df[col] = coerce_numeric_series(df[col])
        df['Avg Forecast'] = df[existing_fc_cols].mean(axis=1)
        print(f"  + Added Avg Forecast")
    else:
        df['Avg Forecast'] = 0

    if 'FaceWt' in df.columns:
        df['FaceWt'] = coerce_numeric_series(df['FaceWt']).fillna(0)
    else:
        df['FaceWt'] = 0
    df['Avg Forecast Lbs'] = df['Avg Forecast'] * FORECAST_LF_TO_SY_FACTOR * (df['FaceWt'] / 16)
    print(f"  + Added Avg Forecast Lbs")
    
    # Calculate Open Tuft LF (sum of PD W 01...20)
    pd_cols = [f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    existing_pd_cols = [col for col in pd_cols if col in df.columns]
    if existing_pd_cols:
        for col in existing_pd_cols:
            df[col] = coerce_numeric_series(df[col])
        df['Open Tuft LF'] = df[existing_pd_cols].sum(axis=1)
        print(f"  + Added Open Tuft LF")
    else:
        df['Open Tuft LF'] = 0
    
    return df

def assign_run_size(avg_forecast_lbs: float, default_run_sizes: dict) -> tuple[str, float]:
    """
    Return (run_size_name, run_size_lbs) for a color group based on its weekly forecast in lbs.

    Parameters
    ----------
    avg_forecast_lbs : float
        Total weekly forecast in lbs for the color group (sum of Avg Forecast Lbs).
    default_run_sizes : dict
        Mapping of tier names to config dicts, each containing:
          - 'run_size_lbs'  : run size in pounds (float)
          - 'lbs_week_min'  : minimum weekly lbs threshold (inclusive)
          - 'lbs_week_max'  : maximum weekly lbs threshold (inclusive), or None for no upper bound

    Returns
    -------
    tuple[str, float]
        (run_size_name, run_size_lbs) for the first matching tier, or the lowest tier as fallback.

    Tiers are evaluated from highest to lowest lbs_week_min so the first match wins.
    """
    sorted_tiers = sorted(
        default_run_sizes.items(),
        key=lambda item: item[1].get('lbs_week_min', 0),
        reverse=True
    )
    for name, cfg in sorted_tiers:
        min_val = cfg.get('lbs_week_min', 0) or 0
        max_val = cfg.get('lbs_week_max')
        if avg_forecast_lbs >= min_val and (max_val is None or avg_forecast_lbs <= max_val):
            return name, float(cfg['run_size_lbs'])
    # Fallback: use lowest tier
    fallback_name, fallback_cfg = sorted_tiers[-1]
    return fallback_name, float(fallback_cfg['run_size_lbs'])


def add_recommendations(df: pd.DataFrame, minimum_weeks: float, target_weeks: float, default_run_sizes: dict) -> pd.DataFrame:
    """Add recommendation logic and related metrics."""
    if df.empty:
        return df

    updated = df.copy()

    if 'ColorGroup_x' in updated.columns and 'ColorGroup' not in updated.columns:
        updated = updated.rename(columns={'ColorGroup_x': 'ColorGroup'})

    for col in ['AsgQty LF', 'ReservedQty LF', 'B/O LF', 'Inv LF', 'Open Tuft LF', 'Avg Forecast', 'Avg Forecast Lbs', 'RollSize', 'FaceWt']:
        if col in updated.columns:
            updated[col] = coerce_numeric_series(updated[col]).fillna(0)

    inv_pos_lf_numerator = (
        updated['Inv LF']
        + updated['Open Tuft LF']
        - updated['B/O LF']
        - updated['ReservedQty LF']
        - updated['AsgQty LF']
    )
    updated['Inv Pos (LF)'] = inv_pos_lf_numerator
    # Convert LF to lbs: LF * (12/9 SY/LF) * (FaceWt oz/SY) / (16 oz/lb)
    # 12-ft-wide carpet: 1 LF = 12 sq ft = 12/9 SY
    updated['Inv Pos (Lbs)'] = updated['Inv Pos (LF)'] / FORECAST_SY_TO_LF_FACTOR * updated['FaceWt'] / 16
    updated['Inv Pos (Wks)'] = np.where(updated['Avg Forecast'] == 0, 0, inv_pos_lf_numerator / updated['Avg Forecast'])

    # --- Color group metrics ---
    # Calculate Color Inv Pos (Wks) and run-size columns per (PlanningGroup, ColorGroup)
    group_keys = ['PlanningGroup', 'ColorGroup']
    if all(k in updated.columns for k in group_keys):
        cg_agg = updated.groupby(group_keys, dropna=False).agg(
            _sum_inv_pos_lbs=('Inv Pos (Lbs)', 'sum'),
            _sum_avg_fc_lbs=('Avg Forecast Lbs', 'sum'),
        ).reset_index()
        cg_agg['ColorGroup.Color Inv Pos (Wks)'] = np.where(
            cg_agg['_sum_avg_fc_lbs'] == 0,
            0,
            cg_agg['_sum_inv_pos_lbs'] / cg_agg['_sum_avg_fc_lbs']
        )

        # Assign run size based on sum(Avg Forecast Lbs) per color group
        run_size_names = []
        run_size_lbs_vals = []
        tufting_prod_sizes = []
        cg_target_weeks = []
        for _, row in cg_agg.iterrows():
            sum_fc_lbs = row['_sum_avg_fc_lbs']
            rs_name, rs_lbs = assign_run_size(sum_fc_lbs, default_run_sizes)
            run_size_names.append(rs_name)
            run_size_lbs_vals.append(rs_lbs)
            # Double the run size if the default run size covers fewer weeks than target
            if sum_fc_lbs > 0 and (rs_lbs / sum_fc_lbs) < target_weeks:
                tps = rs_lbs * 2
            else:
                tps = rs_lbs
            tufting_prod_sizes.append(tps)
            # target_weeks per color group
            cg_tw = (tps / sum_fc_lbs) if sum_fc_lbs > 0 else target_weeks
            cg_target_weeks.append(cg_tw)

        cg_agg['ColorGroup.Run Size'] = run_size_names
        cg_agg['ColorGroup.Run Size (Lbs)'] = run_size_lbs_vals
        cg_agg['ColorGroup.tufting_production_size'] = tufting_prod_sizes
        cg_agg['ColorGroup.target_weeks'] = cg_target_weeks

        cg_merge_cols = group_keys + ['ColorGroup.Color Inv Pos (Wks)', 'ColorGroup.Run Size', 'ColorGroup.Run Size (Lbs)', 'ColorGroup.tufting_production_size', 'ColorGroup.target_weeks']
        updated = updated.merge(cg_agg[cg_merge_cols], on=group_keys, how='left')

        # Sort ColorGroups within each PlanningGroup by ColorGroup.Color Inv Pos (Wks) ascending
        updated = (
            updated
            .sort_values(
                ['PlanningGroup', 'ColorGroup.Color Inv Pos (Wks)', 'ColorGroup', 'Style', 'Color', 'Size', 'Back'],
                ascending=True,
                na_position='last'
            )
            .reset_index(drop=True)
        )
    else:
        updated['ColorGroup.Color Inv Pos (Wks)'] = 0.0
        updated['ColorGroup.Run Size'] = ''
        updated['ColorGroup.Run Size (Lbs)'] = 0.0
        updated['ColorGroup.tufting_production_size'] = 0.0
        updated['ColorGroup.target_weeks'] = target_weeks

    def compute_group_recommendations(group: pd.DataFrame) -> pd.DataFrame:
        group = group.copy().reset_index(drop=True)
        group['RowId'] = range(len(group))
        group['Recommended LF'] = 0.0
        group['Recommended Rolls'] = 0

        def recompute_metrics(local_df: pd.DataFrame) -> pd.DataFrame:
            available = (
                local_df['Inv LF']
                + local_df['Open Tuft LF']
                - local_df['B/O LF']
                - local_df['ReservedQty LF']
                - local_df['AsgQty LF']
                + local_df['Recommended LF']
            )
            local_df['Updated Position'] = np.where(
                local_df['Avg Forecast'] == 0,
                0,
                available / local_df['Avg Forecast']
            )
            return local_df

        group = recompute_metrics(group)
        eligible = group['Avg Forecast'] != 0
        if not eligible.any():
            return group.drop(columns=['RowId'])

        min_position = group.loc[eligible, 'Inv Pos (Wks)'].min()

        # Force a week-1 production cycle if any eligible SKU has an individual
        # backorder line larger than its biggest physical roll on hand.
        force_trigger = False
        if 'Max BO Order LF' in group.columns and 'Max Roll LF' in group.columns:
            effective_bo = np.minimum(
                group.loc[eligible, 'Max BO Order LF'].fillna(0),
                group.loc[eligible, 'RollSize'].fillna(0)
            )
            force_trigger = (effective_bo > group.loc[eligible, 'Max Roll LF'].fillna(0)).any()

        if (pd.isna(min_position) or min_position >= minimum_weeks) and not force_trigger:
            return group.drop(columns=['RowId'])

        # tufting_production_size is the sole driver of total production for a cycle.
        # Fill rolls to the lowest-position SKU until the color group's total
        # recommended lbs reaches tufting_production_size.
        if 'ColorGroup.tufting_production_size' not in group.columns or 'FaceWt' not in group.columns:
            return group.drop(columns=['RowId'])

        tufting_prod_size = float(group['ColorGroup.tufting_production_size'].iloc[0])
        if tufting_prod_size <= 0:
            return group.drop(columns=['RowId'])

        def calc_total_rec_lbs(local_df: pd.DataFrame) -> float:
            return (local_df['Recommended LF'] * FORECAST_LF_TO_SY_FACTOR * local_df['FaceWt'] / 16).sum()

        max_iterations = 10000
        iterations = 0
        total_rec_lbs = calc_total_rec_lbs(group)
        while total_rec_lbs < tufting_prod_size and iterations < max_iterations:
            eligible = group['Avg Forecast'] != 0
            if not eligible.any():
                break
            idx = group.loc[eligible, 'Updated Position'].idxmin()
            group.loc[idx, 'Recommended LF'] = group.loc[idx, 'Recommended LF'] + group.loc[idx, 'RollSize']
            group.loc[idx, 'Recommended Rolls'] = group.loc[idx, 'Recommended Rolls'] + 1
            group = recompute_metrics(group)
            total_rec_lbs = calc_total_rec_lbs(group)
            iterations += 1

        return group.drop(columns=['RowId'])

    if 'PlanningGroup' in updated.columns and 'ColorGroup' in updated.columns:
        updated = updated.groupby(['PlanningGroup', 'ColorGroup'], group_keys=False).apply(compute_group_recommendations)
    else:
        updated['Recommended LF'] = 0
        updated['Recommended Rolls'] = 0

    # Recompute Updated Position vectorially — columns created inside groupby.apply
    # are not always reliably preserved across pandas versions.
    _available = (
        updated['Inv LF']
        + updated['Open Tuft LF']
        - updated['B/O LF']
        - updated['ReservedQty LF']
        - updated['AsgQty LF']
        + updated['Recommended LF']
    )
    updated['Updated Position'] = np.where(
        updated['Avg Forecast'] == 0, 0, _available / updated['Avg Forecast']
    )

    updated['RecommendedLbs'] = updated['Recommended LF'] * FORECAST_LF_TO_SY_FACTOR * (updated['FaceWt'] / 16)
    return updated


def build_projected_production(
    df: pd.DataFrame,
    minimum_weeks: float,
    target_weeks: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build projected production orders and update week projections with those orders.

    1) Tufting orders from existing recommendations (Recommened/Position)
    2) Additional projection orders generated week-by-week by PlanningGroup/ColorGroup
    """
    projected_columns = [
        'OrderType', 'PlanningGroup', 'ColorGroup', 'Style', 'Color',
        'Size', 'Back', 'Week #', 'OrderSize'
    ]

    if df.empty:
        return df, pd.DataFrame(columns=projected_columns)

    updated = df.copy()
    week_cols = [f'Week {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    lead_time_weeks = max(int(minimum_weeks - 1), 0)

    for col in ['PlanningGroup', 'ColorGroup', 'Style', 'Color', 'Size', 'Back']:
        if col not in updated.columns:
            updated[col] = ''

    numeric_cols = ['Avg Forecast', 'RollSize', 'Recommended LF', 'Inv Pos (Wks)'] + week_cols
    for col in numeric_cols:
        if col not in updated.columns:
            updated[col] = 0
        updated[col] = coerce_numeric_series(updated[col]).fillna(0)

    # Ensure per-row ColorGroup.target_weeks is available; fall back to global value
    if 'ColorGroup.target_weeks' not in updated.columns:
        updated['ColorGroup.target_weeks'] = target_weeks
    else:
        updated['ColorGroup.target_weeks'] = coerce_numeric_series(updated['ColorGroup.target_weeks']).fillna(target_weeks)

    tufting_orders = updated.loc[
        updated['Recommended LF'] > 0,
        ['PlanningGroup', 'ColorGroup', 'Style', 'Color', 'Size', 'Back', 'Inv Pos (Wks)', 'Recommended LF']
    ].copy()

    if tufting_orders.empty:
        tufting_orders = pd.DataFrame(columns=projected_columns + ['_RowIdx'])
    else:
        tufting_orders['_RowIdx'] = tufting_orders.index
        tufting_orders['OrderType'] = 'Tufting'
        tufting_orders['Week #'] = tufting_orders['Inv Pos (Wks)'].apply(position_to_week)
        tufting_orders['OrderSize'] = coerce_numeric_series(tufting_orders['Recommended LF']).fillna(0)

        # All SKUs in a color group run together; assign the group's earliest position week to all
        group_min_week = (
            tufting_orders.groupby(['PlanningGroup', 'ColorGroup'])['Week #']
            .min()
            .reset_index()
            .rename(columns={'Week #': '_GroupMinWeek'})
        )
        tufting_orders = tufting_orders.merge(group_min_week, on=['PlanningGroup', 'ColorGroup'], how='left')
        tufting_orders['Week #'] = tufting_orders['_GroupMinWeek'].astype(int)
        tufting_orders.drop(columns=['_GroupMinWeek'], inplace=True)

    # Track which (PlanningGroup, ColorGroup, arrival_week) combos are already scheduled
    # by tufting orders, so the projection loop doesn't double-schedule them.
    handled_group_weeks = set()
    if not tufting_orders.empty:
        for _, tufting_order in tufting_orders.iterrows():
            week_num = int(pd.to_numeric(tufting_order['Week #'], errors='coerce')) if pd.notna(tufting_order['Week #']) else 1
            week_num = max(1, min(week_num, TIME_PHASE_WEEKS))
            handled_group_weeks.add((tufting_order['PlanningGroup'], tufting_order['ColorGroup'], week_num))

    for _, order in tufting_orders.iterrows():
        row_idx = int(order['_RowIdx'])
        week_number = int(pd.to_numeric(order['Week #'], errors='coerce')) if pd.notna(order['Week #']) else 1
        week_number = max(1, min(week_number, TIME_PHASE_WEEKS))
        order_size = float(order['OrderSize'])
        if order_size <= 0:
            continue
        updated.loc[row_idx, week_cols[week_number - 1:]] = updated.loc[row_idx, week_cols[week_number - 1:]] + order_size

    projection_records = []
    group_map = updated.groupby(['PlanningGroup', 'ColorGroup'], dropna=False).groups

    for (pg, cg), group_indices in group_map.items():
        group_indices = list(group_indices)
        eligible_indices = [idx for idx in group_indices if updated.at[idx, 'Avg Forecast'] != 0]
        if not eligible_indices:
            continue

        tufting_prod_size = 0.0
        if 'ColorGroup.tufting_production_size' in updated.columns:
            tufting_prod_size = float(
                coerce_numeric_series(pd.Series([updated.at[eligible_indices[0], 'ColorGroup.tufting_production_size']]))
                .fillna(0).iloc[0]
            )

        for week_number in range(1, TIME_PHASE_WEEKS + 1):
            week_col = week_cols[week_number - 1]
            positions = updated.loc[eligible_indices, week_col] / updated.loc[eligible_indices, 'Avg Forecast']
            min_position = positions.min()
            if pd.isna(min_position) or min_position >= minimum_weeks:
                continue

            arrival_week_number = min(week_number + lead_time_weeks, TIME_PHASE_WEEKS)

            # Skip if this group+week was already scheduled (by a tufting order or earlier projection)
            if (pg, cg, arrival_week_number) in handled_group_weeks:
                continue
            handled_group_weeks.add((pg, cg, arrival_week_number))

            if tufting_prod_size <= 0:
                continue

            arrival_week_col = week_cols[arrival_week_number - 1]

            # Mirror the recommendation logic: fill the lowest-position SKU with rolls
            # until the group's total recommended lbs reaches tufting_production_size.
            # All SKUs that receive rolls get the same arrival week number.
            local_rec = {idx: 0.0 for idx in eligible_indices}
            max_iter = 10000
            it = 0
            while it < max_iter:
                current_total = sum(
                    local_rec[idx] * FORECAST_LF_TO_SY_FACTOR * float(updated.at[idx, 'FaceWt']) / 16
                    for idx in eligible_indices
                )
                if current_total >= tufting_prod_size:
                    break
                min_idx = min(
                    eligible_indices,
                    key=lambda i: (float(updated.at[i, arrival_week_col]) + local_rec[i])
                                  / max(float(updated.at[i, 'Avg Forecast']), 1e-9)
                )
                roll_size = float(updated.at[min_idx, 'RollSize'])
                if roll_size <= 0:
                    break
                local_rec[min_idx] += roll_size
                it += 1

            for idx in eligible_indices:
                order_size = local_rec[idx]
                if order_size <= 0:
                    continue
                updated.loc[idx, week_cols[arrival_week_number - 1:]] = (
                    updated.loc[idx, week_cols[arrival_week_number - 1:]] + order_size
                )
                projection_records.append({
                    'OrderType': 'Projection',
                    'PlanningGroup': pg,
                    'ColorGroup': cg,
                    'Style': updated.at[idx, 'Style'],
                    'Color': updated.at[idx, 'Color'],
                    'Size': updated.at[idx, 'Size'],
                    'Back': updated.at[idx, 'Back'],
                    'Week #': arrival_week_number,
                    'OrderSize': order_size
                })

    projected_frames = []
    if not tufting_orders.empty:
        projected_frames.append(
            tufting_orders[
                ['OrderType', 'PlanningGroup', 'ColorGroup', 'Style', 'Color', 'Size', 'Back', 'Week #', 'OrderSize']
            ]
        )
    if projection_records:
        projected_frames.append(pd.DataFrame(projection_records))

    if projected_frames:
        projected_production = pd.concat(projected_frames, ignore_index=True)
        projected_production['Week #'] = pd.to_numeric(projected_production['Week #'], errors='coerce').fillna(1).astype(int)
        projected_production['OrderSize'] = coerce_numeric_series(projected_production['OrderSize']).fillna(0)
        projected_production = (
            projected_production
            .groupby(
                ['OrderType', 'PlanningGroup', 'ColorGroup', 'Style', 'Color', 'Size', 'Back', 'Week #'],
                as_index=False,
                dropna=False
            )['OrderSize']
            .sum()
            .sort_values(['PlanningGroup', 'ColorGroup', 'Week #', 'OrderType', 'Style', 'Color', 'Size', 'Back'])
            .reset_index(drop=True)
        )
    else:
        projected_production = pd.DataFrame(columns=projected_columns)

    return updated, projected_production

def prune_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop time-phase inputs and auxiliary columns after calculations."""
    drop_cols = []
    drop_cols.extend([f'FC W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)])
    drop_cols.extend([f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)])
    drop_cols.extend([f'SH W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)])
    drop_cols.extend(['PlanGroup', 'ColorGroup_y'])
    existing = [col for col in drop_cols if col in df.columns]
    if existing:
        return df.drop(columns=existing)
    return df

def ensure_planning_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure PlanningGroup and ColorGroup exist after merges."""
    updated = df.copy()

    if 'PlanningGroup' not in updated.columns and 'PlanGroup' in updated.columns:
        updated['PlanningGroup'] = updated['PlanGroup']

    if 'PlanningGroup' in updated.columns and 'PlanGroup' in updated.columns:
        updated['PlanningGroup'] = updated['PlanningGroup'].fillna(updated['PlanGroup'])

    if 'ColorGroup' not in updated.columns:
        if 'ColorGroup_x' in updated.columns:
            updated['ColorGroup'] = updated['ColorGroup_x']
        elif 'ColorGroup_y' in updated.columns:
            updated['ColorGroup'] = updated['ColorGroup_y']

    if 'ColorGroup' in updated.columns:
        if 'ColorGroup_x' in updated.columns:
            updated['ColorGroup'] = updated['ColorGroup'].fillna(updated['ColorGroup_x'])
        if 'ColorGroup_y' in updated.columns:
            updated['ColorGroup'] = updated['ColorGroup'].fillna(updated['ColorGroup_y'])

    drop_merge_suffix_cols = [
        col for col in ['PlanningGroup_x', 'PlanningGroup_y', 'ColorGroup_x', 'ColorGroup_y']
        if col in updated.columns
    ]
    if drop_merge_suffix_cols:
        updated = updated.drop(columns=drop_merge_suffix_cols)

    return updated

def reorder_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns to match the prebuild output layout."""
    preferred = [
        'PlanningGroup', 'ColorGroup', 'Style', 'StyleName', 'Color', 'ColorName',
        'Size', 'Back', 'RollSize', 'FaceWt', 'MachineNum', 'MachineDescription', 'EPN',
        'Avg Forecast', 'Avg Forecast Lbs', 'AsgQty LF', 'ReservedQty LF', 'B/O LF', 'Max BO Order LF', 'Open Tuft LF', 'Inv LF', 'Max Roll LF'
    ]
    preferred.extend([f'Week {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)])
    preferred.extend([
        'Inv Pos (Wks)', 'Inv Pos (LF)', 'Inv Pos (Lbs)',
        'ColorGroup.Color Inv Pos (Wks)', 'ColorGroup.Run Size', 'ColorGroup.Run Size (Lbs)',
        'ColorGroup.tufting_production_size', 'ColorGroup.target_weeks',
        'Recommended LF', 'Recommended Rolls', 'Updated Position', 'RecommendedLbs'
    ])

    existing = [col for col in preferred if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[existing + remaining]

def main():
    """Main execution"""
    print("=" * 70)
    print("CyclePlanner Prebuild Converter - Phase 4")
    print("=" * 70)
    
    # Load configuration
    config = load_config()
    export_folder = Path(config['paths']['export_folder'])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixed_output_path = export_folder / "cycle_planner_prebuild.csv"
    timestamped_output_path = export_folder / f"cycle_planner_prebuild_{timestamp}.csv"
    
    # Load all data sources
    print("\nLoading all data sources...")
    data = load_all_data(export_folder)
    
    # Debug: Check what columns are in time_phase files
    if not data['time_phase_production'].empty:
        print(f"\n  time_phase_production columns: {data['time_phase_production'].columns.tolist()}")
        pd_cols = [f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
        found_cols = [col for col in pd_cols if col in data['time_phase_production'].columns]
        print(f"    Found PD W columns: {found_cols}")
        if found_cols:
            print(f"    Sample PD W 01 values: {data['time_phase_production']['PD W 01'].head().tolist()}")
    
    if not data['time_phase_shipments'].empty:
        print(f"\n  time_phase_shipments columns: {data['time_phase_shipments'].columns.tolist()}")
        sh_cols = [f'SH W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
        found_cols = [col for col in sh_cols if col in data['time_phase_shipments'].columns]
        print(f"    Found SH W columns: {found_cols}")
        if found_cols:
            print(f"    Sample SH W 01 values: {data['time_phase_shipments']['SH W 01'].head().tolist()}")
    
    # Normalize join keys to consistent data types
    print("\nNormalizing join keys...")
    data = normalize_join_keys(data)
    
    # Check if all required files are present
    required_files = ['product_specs', 'inventory', 'sales_forecast', 'mill_orders', 
                     'time_phase_production', 'time_phase_shipments']
    missing = [key for key in required_files if data[key].empty]
    if missing:
        print(f"\n⚠ Warning: Missing data files: {', '.join(missing)}")
        print("  Continuing with available data...")
    
    # Build master dataset
    print("\nBuilding master dataset...")
    planning_groups_df = pd.DataFrame()
    planning_groups_path = Path(config['paths']['planning_groups_xlsx'])
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    if planning_groups_path.exists():
        planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)

    result = build_master_dataset(data, planning_groups_df)
    
    # Add calculated metrics
    print("\nAdding calculated metrics...")
    result = add_calculated_metrics(result)

    # Add time-phased inventory projection
    result = add_time_phased_inventory(result)

    # Ensure planning group columns are present
    result = ensure_planning_columns(result)
    result = apply_planning_groups(result, planning_groups_df)

    # Add recommendations and positions
    params = config.get('parameters', {})
    minimum_weeks = params.get('minimum_weeks', 6)
    target_weeks = params.get('target_weeks', 6)
    default_run_sizes = config.get('default_run_sizes', {})
    print("\nAdding recommendations...")
    result = add_recommendations(result, minimum_weeks, target_weeks, default_run_sizes)

    # Ensure planning group columns are present after recommendations
    result = ensure_planning_columns(result)
    result = apply_planning_groups(result, planning_groups_df)

    # Build projected production output and apply orders to Week 01...20
    print("\nBuilding projected production...")
    result, projected_production = build_projected_production(result, minimum_weeks, target_weeks)

    # Final planning-column normalization before export
    result = ensure_planning_columns(result)

    # Drop time-phased input columns and extra planning-group columns
    result = prune_output_columns(result)

    # Reorder output columns
    result = reorder_output_columns(result)
    
    print(f"\nFinal dataset: {len(result)} rows, {len(result.columns)} columns")
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return

    # Export projected production
    projected_output_path = export_folder / "projected_production.csv"
    projected_timestamped_output_path = export_folder / f"projected_production_{timestamp}.csv"

    print("\nExporting projected production...")
    projected_path, projected_success = export_with_fallback(
        projected_production,
        projected_output_path,
        projected_timestamped_output_path
    )

    if projected_success:
        print(f"✓ Successfully exported projected production to {projected_path}")
        print(f"  Projected production rows: {len(projected_production)}")
    else:
        print("⚠ Failed to export projected production")
    
    # Export to CSV
    print("\nExporting to CSV...")
    output_path, success = export_with_fallback(
        result,
        fixed_output_path,
        timestamped_output_path
    )
    
    if success:
        print(f"✓ Successfully exported to {output_path}")
        
        # Check if fallback was used
        used_fallback = output_path == timestamped_output_path
        if used_fallback:
            print(f"⚠ NOTE: Used fallback filename (primary path was locked)")
        
        print(f"\nSummary:")
        print(f"  Total rows: {len(result)}")
        print(f"  Total columns: {len(result.columns)}")
        print(f"  Projected production rows: {len(projected_production)}")
        print(f"  Key metrics calculated:")
        print(f"    - AsgQty LF, ReservedQty LF, B/O LF, Inv LF")
        print(f"    - Week 01...Week {TIME_PHASE_WEEKS:02d} (inventory projection)")
        print(f"    - Avg Forecast, Open Tuft LF")
        print(f"    - Inv Pos (Wks), Inv Pos (LF), Inv Pos (Lbs)")
        print(f"    - ColorGroup.Color Inv Pos (Wks), ColorGroup.Run Size, ColorGroup.Run Size (Lbs)")
        print(f"    - ColorGroup.tufting_production_size, ColorGroup.target_weeks")
        print(f"    - Recommended LF, Recommended Rolls")
    else:
        print("✗ Failed to export")
        return

if __name__ == "__main__":
    main()