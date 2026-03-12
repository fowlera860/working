"""
Time-Phased Shipments Converter
Pivots mill orders (shipments) to weekly columns (SH W 01 - SH W 20)
Maps to TimePhaseShipments.pq
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
from mill_orders_converter import fetch_all_mill_orders
from utils import get_weeks_out

def create_time_phased_shipments(mill_orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot shipment orders to weekly format
    Each row is a unique combination of Style/Color/Size/Back/Source
    Columns are SH W 01 through SH W 20 with Qty distributed by WeeksOut
    """
    if mill_orders_df.empty:
        return pd.DataFrame()
    
    # Ensure required columns exist
    required_cols = ['Style', 'Color', 'Size', 'Back', 'Qty', 'WeeksOut']
    if not all(col in mill_orders_df.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Have: {mill_orders_df.columns.tolist()}")
    
    # Use pivot_to_weeks utility
    return pivot_to_weeks(
        mill_orders_df,
        value_col='Qty',
        weeks=20,
        prefix='SH '
    )

def main():
    """Main entry point"""
    print("  Loading configuration...")
    config = load_config()
    export_folder = Path(config['paths']['export_folder'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixed_output_path = export_folder / "time_phase_shipments.csv"
    timestamped_output_path = export_folder / f"time_phase_shipments_{timestamp}.csv"
    
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
    
    print("  Fetching mill orders (shipments)...")
    mill_orders_df = fetch_all_mill_orders(planning_groups_df, config)
    
    if not mill_orders_df.empty:
        print("  Creating time-phased view...")
        # Add WeeksOut calculation if not already present
        if 'WeeksOut' not in mill_orders_df.columns:
            mill_orders_df['WeeksOut'] = mill_orders_df['PromDt'].apply(get_weeks_out)
        time_phased_df = create_time_phased_shipments(mill_orders_df)
        
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
                print("  ✗ Failed to export time_phase_shipments.csv")
        else:
            print("  ⚠ No time-phased data generated")
    else:
        print("  ⚠ No mill orders returned")

if __name__ == "__main__":
    main()
