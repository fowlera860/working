"""
Combined MillOrders Converter
Combines all three mill order sources and adds WeeksOut calculation
Replaces CombinedOutgoing.pq
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    get_weeks_out,
    export_with_fallback,
    ensure_export_folder
)

# Import individual converters
import mill_order_production_assignment_converter as mo_pa
import mill_order_roll_assignment_converter as mo_ra
import unassigned_mill_orders_converter as umo

def fetch_all_mill_orders(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Fetch all three mill order types and combine them
    """
    print("Fetching production assignments...")
    pa_df = mo_pa.fetch_mill_order_production_assignment(planning_groups_df, config)
    print(f"  Production assignments: {len(pa_df)} rows")
    
    print("Fetching roll assignments...")
    ra_df = mo_ra.fetch_mill_order_roll_assignment(planning_groups_df, config)
    print(f"  Roll assignments: {len(ra_df)} rows")
    
    print("Fetching unassigned mill orders...")
    uo_df = umo.fetch_unassigned_mill_orders(planning_groups_df, config)
    print(f"  Unassigned orders: {len(uo_df)} rows")
    
    # Normalize column names for production assignments
    if not pa_df.empty:
        pa_df = pa_df.rename(columns={
            'RsvQty': 'RsvQty',
            'PendingProd': 'PendingProd',
            'AsgQty': 'AsgQty',
            'ProdOrder': 'ProdOrder'
        })
        # Add missing columns that unassigned orders don't have
        pa_df['UOM'] = ''
        pa_df['LF'] = 0
    
    # Normalize column names for roll assignments
    if not ra_df.empty:
        ra_df = ra_df.rename(columns={'Qty': 'Qty'})
        # Add missing columns
        ra_df['UOM'] = ''
        ra_df['RsvQty'] = 0
        ra_df['PendingProd'] = 0
        ra_df['AsgQty'] = 0
        ra_df['ProdOrder'] = ''
        ra_df['LF'] = 0
    
    # Normalize column names for unassigned orders
    if not uo_df.empty:
        uo_df = uo_df.rename(columns={'Qty': 'Qty', 'UOM': 'UOM'})
        # Add missing columns
        uo_df['RsvQty'] = 0
        uo_df['PendingProd'] = 0
        uo_df['AsgQty'] = 0
        uo_df['ProdOrder'] = ''
        # LF calculation will be done after (requires Product_Specs join)
        uo_df['LF'] = 0
    
    # Combine all three dataframes
    combined_cols = [
        'Style', 'Color', 'Size', 'Back', 'Src', 'OrdNum', 'OrdLine',
        'Qty', 'UOM', 'PromDt', 'RsvQty', 'PendingProd', 'AsgQty', 'ProdOrder', 'LF'
    ]
    
    dfs_to_combine = []
    
    if not pa_df.empty:
        dfs_to_combine.append(pa_df[[col for col in combined_cols if col in pa_df.columns]])
    
    if not ra_df.empty:
        dfs_to_combine.append(ra_df[[col for col in combined_cols if col in ra_df.columns]])
    
    if not uo_df.empty:
        dfs_to_combine.append(uo_df[[col for col in combined_cols if col in uo_df.columns]])
    
    if dfs_to_combine:
        combined = pd.concat(dfs_to_combine, ignore_index=True)
    else:
        combined = pd.DataFrame()
    
    return combined

def add_weeks_out(df: pd.DataFrame) -> pd.DataFrame:
    """Add WeeksOut calculation to dataframe"""
    if df.empty:
        return df
    
    df['WeeksOut'] = df['PromDt'].apply(get_weeks_out)
    return df

def main():
    """Main execution"""
    # Load configuration
    config = load_config()
    
    # Get paths from config
    planning_groups_path = Path(config['paths']['planning_groups_xlsx'])
    export_folder = Path(config['paths']['export_folder'])
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    
    # Create output paths
    fixed_output_path = export_folder / "mill_orders.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"mill_orders_{timestamp}.csv"
    
    print("=" * 60)
    print("Combined Mill Orders Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch all mill orders
    print("\nFetching all mill order types...")
    combined_df = fetch_all_mill_orders(planning_groups_df, config)
    
    if combined_df.empty:
        print("No data returned from database or connection failed")
        return
    
    print(f"\nCombined: {len(combined_df)} total rows")
    
    # Add WeeksOut calculation
    print("Adding WeeksOut calculation...")
    combined_df = add_weeks_out(combined_df)
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return
    
    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        combined_df,
        fixed_output_path,
        timestamped_output_path
    )
    
    if not success:
        return
    
    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(combined_df)}")
    print("\nFirst few rows:")
    print(combined_df.head(10))
    print("\nColumn info:")
    print(combined_df.dtypes)
    print("\nSource breakdown:")
    print(combined_df['Src'].value_counts())

if __name__ == "__main__":
    main()
