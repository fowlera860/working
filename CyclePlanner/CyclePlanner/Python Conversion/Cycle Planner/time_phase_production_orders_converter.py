"""
Time-Phased Production Orders Converter
Pivots production orders to weekly columns (PD W 01 - PD W 20)
Maps to TimePhaseProductionOrders.pq
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    pivot_to_weeks,
    export_with_fallback,
    ensure_export_folder
)
from production_orders_converter import fetch_production_orders, process_production_orders

def create_time_phased_production_orders(production_orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot production orders to weekly format
    Each row is a unique combination of Style/Color/Size/Back/ProdOrderNum
    Columns are PD W 01 through PD W 20 with OrderQty distributed by WeeksOut
    """
    if production_orders_df.empty:
        return pd.DataFrame()
    
    # Prefer planning-group keys so x-ref production maps back to base SKU in prebuild.
    pg_key_cols = ['PGSTYL', 'PGCLR', 'PGSIZE', 'PGBACK']
    base_key_cols = ['Style', 'Color', 'Size', 'Back']
    key_cols = pg_key_cols if all(col in production_orders_df.columns for col in pg_key_cols) else base_key_cols

    # Ensure required columns exist
    required_cols = key_cols + ['OrderQty', 'WeeksOut']
    if not all(col in production_orders_df.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Have: {production_orders_df.columns.tolist()}")
    
    # Use pivot_to_weeks utility
    return pivot_to_weeks(
        production_orders_df,
        value_col='OrderQty',
        weeks=20,
        prefix='PD ',
        key_cols=key_cols
    )

def main():
    """Main entry point"""
    print("  Loading configuration...")
    config = load_config()
    export_folder = Path(config['paths']['export_folder'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixed_output_path = export_folder / "time_phase_production_orders.csv"
    timestamped_output_path = export_folder / f"time_phase_production_orders_{timestamp}.csv"
    
    print("  Loading planning groups...")
    planning_groups_path = config['paths']['planning_groups_xlsx']
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    
    # Check if planning groups file exists first
    planning_groups_path_obj = Path(planning_groups_path)
    if not planning_groups_path_obj.exists():
        print(f"  ⚠ Planning Groups file not found at {planning_groups_path}")
        print("  (This is expected in dev/test environments)")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    
    print("  Fetching production orders...")
    production_orders_df = fetch_production_orders(planning_groups_df)
    
    if not production_orders_df.empty:
        print("  Processing production orders...")
        production_orders_df = process_production_orders(production_orders_df)
        
        print("  Creating time-phased view...")
        time_phased_df = create_time_phased_production_orders(production_orders_df)
        
        if not time_phased_df.empty:
            print("  Exporting to CSV...")
            ensure_export_folder(export_folder)
            output_path, ok = export_with_fallback(
                time_phased_df,
                fixed_output_path,
                timestamped_output_path
            )
            if ok and output_path is not None:
                print(f"  ✓ Exported {len(time_phased_df)} rows to {output_path}")
            else:
                print("  ✗ Failed to export time_phase_production_orders.csv")
        else:
            print("  ⚠ No time-phased data generated")
    else:
        print("  ⚠ No production orders returned")

if __name__ == "__main__":
    main()
