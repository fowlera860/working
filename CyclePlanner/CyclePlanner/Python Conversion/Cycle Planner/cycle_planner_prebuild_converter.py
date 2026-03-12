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
        asg_summary.rename(columns={'PendingProd': 'AsgQty', 'RsvQty': 'ReservedQty'}, inplace=True)
        result = result.merge(asg_summary, on=join_keys, how='left')
        print(f"  + Added AsgQty and ReservedQty")
    else:
        result['AsgQty'] = 0
        result['ReservedQty'] = 0
    
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
        bo_summary.rename(columns={'Calc': 'B/O'}, inplace=True)
        result = result.merge(bo_summary, on=join_keys, how='left')
        print(f"  + Added B/O")
    else:
        result['B/O'] = 0
    
    # 3. Calculate OnHand from Inventory
    if not data['inventory'].empty:
        # Check which column name is used (Feet or FeetAvailable)
        feet_col = 'Feet' if 'Feet' in data['inventory'].columns else 'FeetAvailable'
        if feet_col not in data['inventory'].columns:
            print(f"  ⚠ Warning: Neither 'Feet' nor 'FeetAvailable' found in inventory")
            print(f"    Available columns: {data['inventory'].columns.tolist()}")
            result['OnHand'] = 0
        else:
            inventory_summary = data['inventory'].groupby(join_keys)[feet_col].sum().reset_index()
            inventory_summary.rename(columns={feet_col: 'OnHand'}, inplace=True)
            result = result.merge(inventory_summary, on=join_keys, how='left')
            print(f"  + Added OnHand")
    else:
        result['OnHand'] = 0
    
    # Replace null OnHand with 0
    result['OnHand'] = result['OnHand'].fillna(0)
    
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

    for col in ['OnHand', 'B/O', 'ReservedQty', 'AsgQty', 'Total Production']:
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
        has_total_production = 'Total Production' in df.columns
        if has_total_production:
            on_hand = (
                row.get('OnHand', 0)
                + row.get('Total Production', 0)
                - row.get('B/O', 0)
                - row.get('ReservedQty', 0)
                - row.get('AsgQty', 0)
            )
        else:
            on_hand = row.get('OnHand', 0)
        
        # Get forecast, production, and shipments as dictionaries
        forecast_row = {col: row.get(col, 0) for col in fc_cols}
        if has_total_production:
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
    
    # Calculate Total Production (sum of PD W 01...20)
    pd_cols = [f'PD W {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)]
    existing_pd_cols = [col for col in pd_cols if col in df.columns]
    if existing_pd_cols:
        for col in existing_pd_cols:
            df[col] = coerce_numeric_series(df[col])
        df['Total Production'] = df[existing_pd_cols].sum(axis=1)
        print(f"  + Added Total Production")
    else:
        df['Total Production'] = 0
    
    return df

def add_recommendations(df: pd.DataFrame, minimum_weeks: float, target_weeks: float) -> pd.DataFrame:
    """Add recommendation logic and related metrics."""
    if df.empty:
        return df

    updated = df.copy()

    if 'ColorGroup_x' in updated.columns and 'ColorGroup' not in updated.columns:
        updated = updated.rename(columns={'ColorGroup_x': 'ColorGroup'})

    for col in ['AsgQty', 'ReservedQty', 'B/O', 'OnHand', 'Total Production', 'Avg Forecast', 'RollSize', 'FaceWt']:
        if col in updated.columns:
            updated[col] = coerce_numeric_series(updated[col]).fillna(0)

    position_numerator = (
        updated['OnHand']
        + updated['Total Production']
        - updated['B/O']
        - updated['ReservedQty']
        - updated['AsgQty']
    )
    updated['Position'] = np.where(updated['Avg Forecast'] == 0, 0, position_numerator / updated['Avg Forecast'])

    def compute_group_recommendations(group: pd.DataFrame) -> pd.DataFrame:
        group = group.copy().reset_index(drop=True)
        group['RowId'] = range(len(group))
        group['Recommened'] = 0.0

        def recompute_metrics(local_df: pd.DataFrame) -> pd.DataFrame:
            available = (
                local_df['OnHand']
                + local_df['Total Production']
                - local_df['B/O']
                - local_df['ReservedQty']
                - local_df['AsgQty']
                + local_df['Recommened']
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

        min_position = group.loc[eligible, 'Position'].min()
        if pd.isna(min_position) or min_position >= minimum_weeks:
            return group.drop(columns=['RowId'])

        max_iterations = 10000
        iterations = 0
        while iterations < max_iterations:
            eligible = group['Avg Forecast'] != 0
            if not eligible.any():
                break

            min_updated = group.loc[eligible, 'Updated Position'].min()
            if pd.isna(min_updated) or min_updated > target_weeks:
                break

            candidates = group.loc[eligible & (group['Updated Position'] == min_updated)]
            if candidates.empty:
                break

            idx = candidates.index[0]
            group.loc[idx, 'Recommened'] = group.loc[idx, 'Recommened'] + group.loc[idx, 'RollSize']
            group = recompute_metrics(group)
            iterations += 1

        return group.drop(columns=['RowId'])

    if 'PlanningGroup' in updated.columns and 'ColorGroup' in updated.columns:
        updated = updated.groupby(['PlanningGroup', 'ColorGroup'], group_keys=False).apply(compute_group_recommendations)
    else:
        updated['Recommened'] = 0
        updated['Updated Position'] = updated.get('Position', 0)

    updated['RecommendedLbs'] = updated['Recommened'] * FORECAST_LF_TO_SY_FACTOR * (updated['FaceWt'] / 16)
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

    numeric_cols = ['Avg Forecast', 'RollSize', 'Recommened', 'Position'] + week_cols
    for col in numeric_cols:
        if col not in updated.columns:
            updated[col] = 0
        updated[col] = coerce_numeric_series(updated[col]).fillna(0)

    tufting_orders = updated.loc[
        updated['Recommened'] > 0,
        ['PlanningGroup', 'ColorGroup', 'Style', 'Color', 'Size', 'Back', 'Position', 'Recommened']
    ].copy()

    if tufting_orders.empty:
        tufting_orders = pd.DataFrame(columns=projected_columns + ['_RowIdx'])
    else:
        tufting_orders['_RowIdx'] = tufting_orders.index
        tufting_orders['OrderType'] = 'Tufting'
        tufting_orders['Week #'] = tufting_orders['Position'].apply(position_to_week)
        tufting_orders['OrderSize'] = coerce_numeric_series(tufting_orders['Recommened']).fillna(0)

    tufting_week_keys = set()
    if not tufting_orders.empty:
        for _, tufting_order in tufting_orders.iterrows():
            row_idx = int(tufting_order['_RowIdx'])
            week_num = int(pd.to_numeric(tufting_order['Week #'], errors='coerce')) if pd.notna(tufting_order['Week #']) else 1
            if week_num < 1:
                week_num = 1
            if week_num > TIME_PHASE_WEEKS:
                week_num = TIME_PHASE_WEEKS
            tufting_week_keys.add((row_idx, week_num))

    for _, order in tufting_orders.iterrows():
        row_idx = int(order['_RowIdx'])
        week_number = int(pd.to_numeric(order['Week #'], errors='coerce')) if pd.notna(order['Week #']) else 1
        if week_number < 1:
            week_number = 1
        if week_number > TIME_PHASE_WEEKS:
            week_number = TIME_PHASE_WEEKS
        order_size = float(order['OrderSize'])
        if order_size <= 0:
            continue
        updated.loc[row_idx, week_cols[week_number - 1:]] = updated.loc[row_idx, week_cols[week_number - 1:]] + order_size

    projection_records = []
    group_map = updated.groupby(['PlanningGroup', 'ColorGroup'], dropna=False).groups

    for _, group_indices in group_map.items():
        group_indices = list(group_indices)
        eligible_indices = [idx for idx in group_indices if updated.at[idx, 'Avg Forecast'] != 0]
        if not eligible_indices:
            continue

        for week_number in range(1, TIME_PHASE_WEEKS + 1):
            week_col = week_cols[week_number - 1]
            positions = updated.loc[eligible_indices, week_col] / updated.loc[eligible_indices, 'Avg Forecast']
            min_position = positions.min()
            if pd.isna(min_position) or min_position >= minimum_weeks:
                continue

            arrival_week_number = min(week_number + lead_time_weeks, TIME_PHASE_WEEKS)
            arrival_week_col = week_cols[arrival_week_number - 1]

            for selected_idx in eligible_indices:
                avg_forecast = float(updated.at[selected_idx, 'Avg Forecast'])
                roll_size = float(updated.at[selected_idx, 'RollSize'])

                if (int(selected_idx), arrival_week_number) in tufting_week_keys:
                    continue

                if avg_forecast <= 0 or roll_size <= 0:
                    continue

                current_position = float(updated.at[selected_idx, arrival_week_col]) / avg_forecast
                if current_position >= target_weeks:
                    continue

                target_inventory = target_weeks * avg_forecast
                shortfall = target_inventory - float(updated.at[selected_idx, arrival_week_col])
                if shortfall <= 0:
                    continue

                order_count = int(np.ceil(shortfall / roll_size))
                order_size = order_count * roll_size
                if order_size <= 0:
                    continue

                updated.loc[selected_idx, week_cols[arrival_week_number - 1:]] = (
                    updated.loc[selected_idx, week_cols[arrival_week_number - 1:]] + order_size
                )

                projection_records.append({
                    'OrderType': 'Projection',
                    'PlanningGroup': updated.at[selected_idx, 'PlanningGroup'],
                    'ColorGroup': updated.at[selected_idx, 'ColorGroup'],
                    'Style': updated.at[selected_idx, 'Style'],
                    'Color': updated.at[selected_idx, 'Color'],
                    'Size': updated.at[selected_idx, 'Size'],
                    'Back': updated.at[selected_idx, 'Back'],
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
        'Avg Forecast', 'Avg Forecast Lbs', 'AsgQty', 'ReservedQty', 'B/O', 'Total Production', 'OnHand'
    ]
    preferred.extend([f'Week {i:02d}' for i in range(1, TIME_PHASE_WEEKS + 1)])
    preferred.extend(['Position', 'Recommened', 'Updated Position', 'RecommendedLbs'])

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
    print("\nAdding recommendations...")
    result = add_recommendations(result, minimum_weeks, target_weeks)

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
        print(f"    - AsgQty, ReservedQty, B/O, OnHand")
        print(f"    - Week 01...Week {TIME_PHASE_WEEKS:02d} (inventory projection)")
        print(f"    - Avg Forecast, Total Production")
    else:
        print("✗ Failed to export")
        return

if __name__ == "__main__":
    main()
