"""
Test script for Phase 2 - Mill Orders Converters
Uses mock data to verify workflow
"""

import pandas as pd
from datetime import datetime, timedelta
from utils import get_weeks_out

def create_mock_production_assignments() -> pd.DataFrame:
    """Create mock production assignments"""
    data = {
        'Style': ['9223', '9224', '9225'],
        'Color': ['00310', '00311', '00312'],
        'Size': ['1200', '1200', '1200'],
        'Back': ['08', '08', '08'],
        'OrdNum': [100001, 100002, 100003],
        'OrdLine': [1, 1, 1],
        'ProdOrder': ['PO001', 'PO002', 'PO003'],
        'AsgQty': [500, 600, 700],
        'PromDt': [datetime.now().date() + timedelta(days=7), 
                   datetime.now().date() + timedelta(days=14),
                   datetime.now().date() + timedelta(days=21)],
        'RsvQty': [100, 150, 200],
        'PendingProd': [400, 450, 500],
        'Src': ['Production Assignment', 'Production Assignment', 'Production Assignment']
    }
    return pd.DataFrame(data)

def create_mock_roll_assignments() -> pd.DataFrame:
    """Create mock roll assignments"""
    data = {
        'Style': ['9223', '9224'],
        'Color': ['00310', '00311'],
        'Size': ['1200', '1200'],
        'Back': ['08', '08'],
        'OrdNum': [200001, 200002],
        'OrdLine': [1, 1],
        'Qty': [250, 300],
        'PromDt': [datetime.now().date() + timedelta(days=3),
                   datetime.now().date() + timedelta(days=10)],
        'Src': ['Roll Reserve', 'Roll Reserve']
    }
    return pd.DataFrame(data)

def create_mock_unassigned_orders() -> pd.DataFrame:
    """Create mock unassigned mill orders"""
    data = {
        'Style': ['9225', '9223'],
        'Color': ['00312', '00310'],
        'Size': ['1200', '1200'],
        'Back': ['08', '08'],
        'OrdNum': [300001, 300002],
        'OrdLine': [1, 2],
        'Qty': [100, 150],
        'UOM': ['RL', 'LF'],
        'PromDt': [datetime.now().date() + timedelta(days=5),
                   datetime.now().date() + timedelta(days=12)],
        'Src': ['Unassigned', 'Unassigned']
    }
    return pd.DataFrame(data)

def test_workflow():
    """Test Phase 2 workflow"""
    print("=" * 60)
    print("Testing Phase 2 Converters - Mill Orders")
    print("=" * 60)
    
    # Create mock data
    print("\n1. Creating mock data...")
    pa_df = create_mock_production_assignments()
    ra_df = create_mock_roll_assignments()
    uo_df = create_mock_unassigned_orders()
    
    print(f"   Production Assignments: {len(pa_df)} rows")
    print(f"   Roll Assignments: {len(ra_df)} rows")
    print(f"   Unassigned Orders: {len(uo_df)} rows")
    
    # Test combining
    print("\n2. Testing combine logic...")
    
    # Normalize columns
    pa_cols = pa_df[['Style', 'Color', 'Size', 'Back', 'Src', 'OrdNum', 'OrdLine', 'AsgQty', 'PromDt']]
    ra_cols = ra_df[['Style', 'Color', 'Size', 'Back', 'Src', 'OrdNum', 'OrdLine', 'Qty', 'PromDt']]
    uo_cols = uo_df[['Style', 'Color', 'Size', 'Back', 'Src', 'OrdNum', 'OrdLine', 'Qty', 'PromDt']]
    
    combined = pd.concat([pa_cols, ra_cols, uo_cols], ignore_index=True)
    print(f"   Combined: {len(combined)} rows")
    print(f"   Sources: {combined['Src'].value_counts().to_dict()}")
    
    # Test WeeksOut calculation
    print("\n3. Testing WeeksOut calculation...")
    combined['WeeksOut'] = combined['PromDt'].apply(get_weeks_out)
    
    print(f"   Sample WeeksOut values:")
    for idx, row in combined.head(3).iterrows():
        print(f"     PromDt: {row['PromDt']}, WeeksOut: {row['WeeksOut']}")
    
    print(f"   Min WeeksOut: {combined['WeeksOut'].min()}")
    print(f"   Max WeeksOut: {combined['WeeksOut'].max()}")
    
    # Test export
    print("\n4. Testing export...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_output/mill_orders_test_{timestamp}.csv"
    combined.to_csv(output_file, index=False)
    
    # Verify
    print("\n5. Verifying export...")
    loaded = pd.read_csv(output_file)
    print(f"   Loaded: {len(loaded)} rows, {len(loaded.columns)} columns")
    print(f"   Columns: {loaded.columns.tolist()}")
    
    print("\n✓ Phase 2 workflow test complete!")
    print(f"   Test file: {output_file}")
    return True

if __name__ == "__main__":
    import os
    os.makedirs("test_output", exist_ok=True)
    test_workflow()
