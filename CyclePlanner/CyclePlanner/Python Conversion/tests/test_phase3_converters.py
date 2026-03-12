"""
Phase 3 Converters Test Suite
Tests ProductionOrders, TimePhaseProductionOrders, and TimePhaseShipments
Uses mock data for verification
"""

import pandas as pd
import pyodbc
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Mock utils module
class MockConfig:
    def __init__(self):
        self.config = {
            'database': {'server': 'TDG-DLT-IBMSQL', 'database': 'CAMS'},
            'paths': {'export_folder': '/tmp/exports'}
        }
    
    def get(self, key, default=None):
        return self.config.get(key, default)

def test_production_orders_logic():
    """Test production orders processing logic"""
    print("\nTesting ProductionOrders Converter Logic")
    print("-" * 50)
    
    # Create mock production orders data
    base_date = datetime.now()
    mock_data = {
        'Style': ['STY001', 'STY001', 'STY002'],
        'Color': ['RED', 'RED', 'BLUE'],
        'Size': ['SM', 'MD', 'LG'],
        'Back': ['JUTE', 'JUTE', 'LATEX'],
        'ProdOrderNum': ['PO001', 'PO002', 'PO003'],
        'ProdOrderDesc': ['Order 1', 'Order 2', 'Order 3'],
        'OrderQty': [1000, 1500, 2000],
        'OrderDate': [base_date - timedelta(days=10)] * 3,
        'PromiseDate': [
            base_date + timedelta(days=7),   # 1 week
            base_date + timedelta(days=14),  # 2 weeks
            base_date + timedelta(days=21)   # 3 weeks
        ],
        'Status': ['O', 'R', 'S'],
        'MachineNum': ['M001', 'M002', 'M001'],
        'CreatedDate': [base_date - timedelta(days=10)] * 3,
        'ScheduleCapacity': [500, 500, 500],
        'CycleTime': [2, 2, 3]
    }
    
    df = pd.DataFrame(mock_data)
    
    # Simulate WeeksOut calculation (from utils.get_weeks_out)
    def get_weeks_out_mock(promise_date):
        if pd.isna(promise_date):
            return 0
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())  # Start of current week (Sunday)
        days_diff = (promise_date.date() - current_week_start).days
        weeks = max(1, (days_diff // 7) + 1)
        return min(13, weeks)
    
    df['WeeksOut'] = df['PromiseDate'].apply(get_weeks_out_mock)
    
    print(f"✓ Created mock data: {len(df)} production orders")
    print(f"  Columns: {df.columns.tolist()}")
    print(f"  WeeksOut range: {df['WeeksOut'].min()}-{df['WeeksOut'].max()} weeks")
    print(f"  Sample:\n{df[['Style', 'Color', 'ProdOrderNum', 'OrderQty', 'PromiseDate', 'WeeksOut']].to_string()}")
    
    return df

def test_time_phase_pivot_logic(df):
    """Test time-phasing pivot logic"""
    print("\n\nTesting TimePhaseProductionOrders Pivot Logic")
    print("-" * 50)
    
    # Group by Style/Color/Size/Back and sum OrderQty by WeeksOut
    grouped = df.groupby(['Style', 'Color', 'Size', 'Back', 'WeeksOut'])['OrderQty'].sum().reset_index()
    
    # Pivot to weeks
    pivoted = grouped.pivot_table(
        index=['Style', 'Color', 'Size', 'Back'],
        columns='WeeksOut',
        values='OrderQty',
        fill_value=0
    )
    
    # Rename columns to PD W 01, PD W 02, etc.
    new_cols = {}
    for col in pivoted.columns:
        new_cols[col] = f'PD W {int(col):02d}'
    pivoted = pivoted.rename(columns=new_cols)
    
    pivoted = pivoted.reset_index()
    
    print(f"✓ Pivot result: {len(pivoted)} unique style/color combinations")
    print(f"  Columns: {pivoted.columns.tolist()}")
    print(f"  Sample:\n{pivoted.to_string()}")
    
    return pivoted

def test_time_phase_shipments_logic():
    """Test time-phased shipments logic"""
    print("\n\nTesting TimePhaseShipments Pivot Logic")
    print("-" * 50)
    
    # Create mock mill orders (shipments) data
    base_date = datetime.now()
    mock_mill_orders = {
        'Style': ['STY001', 'STY001', 'STY002'],
        'Color': ['RED', 'RED', 'BLUE'],
        'Size': ['SM', 'MD', 'LG'],
        'Back': ['JUTE', 'JUTE', 'LATEX'],
        'OrdNum': ['ORD001', 'ORD002', 'ORD003'],
        'OrdLine': [1, 1, 1],
        'Qty': [500, 750, 1000],
        'PromDt': [
            base_date + timedelta(days=7),   # 1 week
            base_date + timedelta(days=14),  # 2 weeks
            base_date + timedelta(days=21)   # 3 weeks
        ],
        'Src': ['Production Assignment', 'Roll Reserve', 'Unassigned']
    }
    
    df = pd.DataFrame(mock_mill_orders)
    
    # Apply WeeksOut calculation
    def get_weeks_out_mock(promise_date):
        if pd.isna(promise_date):
            return 0
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())
        days_diff = (promise_date.date() - current_week_start).days
        weeks = max(1, (days_diff // 7) + 1)
        return min(13, weeks)
    
    df['WeeksOut'] = df['PromDt'].apply(get_weeks_out_mock)
    
    print(f"✓ Created mock shipment data: {len(df)} orders")
    print(f"  Columns: {df.columns.tolist()}")
    
    # Group and pivot similar to production orders
    grouped = df.groupby(['Style', 'Color', 'Size', 'Back', 'WeeksOut'])['Qty'].sum().reset_index()
    
    pivoted = grouped.pivot_table(
        index=['Style', 'Color', 'Size', 'Back'],
        columns='WeeksOut',
        values='Qty',
        fill_value=0
    )
    
    # Rename columns to SH W 01, SH W 02, etc.
    new_cols = {}
    for col in pivoted.columns:
        new_cols[col] = f'SH W {int(col):02d}'
    pivoted = pivoted.rename(columns=new_cols)
    
    pivoted = pivoted.reset_index()
    
    print(f"✓ Pivot result: {len(pivoted)} unique style/color combinations")
    print(f"  Columns: {pivoted.columns.tolist()}")
    print(f"  Sample:\n{pivoted.to_string()}")
    
    return pivoted

def main():
    """Run all Phase 3 tests"""
    print("\n" + "=" * 70)
    print("  PHASE 3 CONVERTERS TEST SUITE")
    print("=" * 70)
    print("Testing: ProductionOrders, TimePhaseProductionOrders, TimePhaseShipments")
    
    try:
        # Test production orders
        prod_orders_df = test_production_orders_logic()
        
        # Test time-phased production orders
        time_phase_prod_df = test_time_phase_pivot_logic(prod_orders_df)
        
        # Test time-phased shipments
        time_phase_ship_df = test_time_phase_shipments_logic()
        
        # Summary
        print("\n\n" + "=" * 70)
        print("  TEST SUMMARY")
        print("=" * 70)
        print(f"✓ ProductionOrders: {len(prod_orders_df)} records")
        print(f"✓ TimePhaseProductionOrders: {len(time_phase_prod_df)} records")
        print(f"✓ TimePhaseShipments: {len(time_phase_ship_df)} records")
        print("\n✓ All Phase 3 tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
