"""
Test Phase 4: CyclePlanner Prebuild Converter
Tests the master consolidation logic with mock data
"""

import pandas as pd
import numpy as np
from cycle_planner_prebuild_converter import (
    calculate_time_phased_inventory,
    build_master_dataset,
    add_time_phased_inventory
)

def test_time_phased_inventory_calculation():
    """Test the time-phased inventory calculation function"""
    print("=" * 70)
    print("Test 1: Time-Phased Inventory Calculation")
    print("=" * 70)
    
    # Test case: Start with 1000 on hand
    # Week 1: Forecast 100, Production 200, Shipments 50
    # Expected: 1000 - 100 + 200 - 50 = 1050
    
    on_hand = 1000
    forecast = {f'FC W {i:02d}': 100 for i in range(1, 13)}
    production = {f'PD W {i:02d}': 200 for i in range(1, 13)}
    shipments = {f'SH W {i:02d}': 50 for i in range(1, 13)}
    
    result = calculate_time_phased_inventory(on_hand, forecast, production, shipments)
    
    print(f"Initial OnHand: {on_hand}")
    print(f"Per Week: -100 (forecast) +200 (production) -50 (shipments) = +50 net")
    print(f"\nProjected Inventory:")
    for week, value in result.items():
        print(f"  {week}: {value:.2f}")
    
    # Week 1 should be 1050
    assert result['Week 01'] == 1050, f"Week 01 should be 1050, got {result['Week 01']}"
    # Week 12 should be 1600 (1000 + 50*12)
    assert result['Week 12'] == 1600, f"Week 12 should be 1600, got {result['Week 12']}"
    
    print("\n✓ Time-phased calculation test passed!")
    return True

def test_depletion_scenario():
    """Test scenario where inventory depletes"""
    print("\n" + "=" * 70)
    print("Test 2: Inventory Depletion Scenario")
    print("=" * 70)
    
    on_hand = 500
    forecast = {f'FC W {i:02d}': 100 for i in range(1, 13)}  # High demand
    production = {f'PD W {i:02d}': 50 for i in range(1, 13)}  # Low production
    shipments = {f'SH W {i:02d}': 0 for i in range(1, 13)}
    
    result = calculate_time_phased_inventory(on_hand, forecast, production, shipments)
    
    print(f"Initial OnHand: {on_hand}")
    print(f"Per Week: -100 (forecast) +50 (production) = -50 net")
    print(f"\nProjected Inventory:")
    for i, (week, value) in enumerate(result.items(), 1):
        print(f"  {week}: {value:.2f}")
        if i >= 10 and value < 0:
            print(f"    ⚠ Stockout warning!")
    
    # Week 1 should be 450 (500 - 50)
    assert result['Week 01'] == 450, f"Week 01 should be 450, got {result['Week 01']}"
    # Week 10 should be 0 (500 - 50*10)
    assert result['Week 10'] == 0, f"Week 10 should be 0, got {result['Week 10']}"
    # Week 11 should be -50
    assert result['Week 11'] == -50, f"Week 11 should be -50, got {result['Week 11']}"
    # Week 12 should be -100 (negative inventory)
    assert result['Week 12'] == -100, f"Week 12 should be -100, got {result['Week 12']}"
    
    print("\n✓ Depletion scenario test passed!")
    return True

def test_master_dataset_build():
    """Test building master dataset from multiple sources"""
    print("\n" + "=" * 70)
    print("Test 3: Master Dataset Build")
    print("=" * 70)
    
    # Create mock data
    product_specs = pd.DataFrame({
        'Style': ['A100', 'A200', 'A300'],
        'Color': ['RED', 'BLUE', 'GREEN'],
        'Size': ['12X12', '12X12', '15X15'],
        'Back': ['J', 'J', 'A'],
        'RollSize': [100, 100, 150],
        'StyleName': ['Product A', 'Product B', 'Product C']
    })
    
    # Mill orders - production assignment
    mill_orders_pa = pd.DataFrame({
        'Style': ['A100', 'A200'],
        'Color': ['RED', 'BLUE'],
        'Size': ['12X12', '12X12'],
        'Back': ['J', 'J'],
        'Src': ['Production Assignment', 'Production Assignment'],
        'PendingProd': [500, 300],
        'RsvQty': [200, 100]
    })
    
    # Mill orders - unassigned
    mill_orders_unassigned = pd.DataFrame({
        'Style': ['A100', 'A300'],
        'Color': ['RED', 'GREEN'],
        'Size': ['12X12', '15X15'],
        'Back': ['J', 'A'],
        'Src': ['Unassigned', 'Unassigned'],
        'Qty': [10, 5],
        'UOM': ['RL', 'LF']
    })
    
    mill_orders = pd.concat([mill_orders_pa, mill_orders_unassigned], ignore_index=True)
    
    # Inventory
    inventory = pd.DataFrame({
        'Style': ['A100', 'A100', 'A200'],
        'Color': ['RED', 'RED', 'BLUE'],
        'Size': ['12X12', '12X12', '12X12'],
        'Back': ['J', 'J', 'J'],
        'FeetAvailable': [100, 150, 200]
    })
    
    # Sales forecast
    sales_forecast = pd.DataFrame({
        'Style': ['A100', 'A200'],
        'Color': ['RED', 'BLUE'],
        'Size': ['12X12', '12X12'],
        'Back': ['J', 'J'],
        'FC W 01': [50, 60],
        'FC W 02': [55, 65]
    })
    
    # Time-phased production
    time_phase_prod = pd.DataFrame({
        'Style': ['A100', 'A200'],
        'Color': ['RED', 'BLUE'],
        'Size': ['12X12', '12X12'],
        'Back': ['J', 'J'],
        'PD W 01': [100, 80],
        'PD W 02': [120, 90]
    })
    
    # Time-phased shipments
    time_phase_ship = pd.DataFrame({
        'Style': ['A100', 'A200'],
        'Color': ['RED', 'BLUE'],
        'Size': ['12X12', '12X12'],
        'Back': ['J', 'J'],
        'SH W 01': [30, 25],
        'SH W 02': [35, 30]
    })
    
    data = {
        'product_specs': product_specs,
        'inventory': inventory,
        'sales_forecast': sales_forecast,
        'mill_orders': mill_orders,
        'production_orders': pd.DataFrame(),
        'time_phase_production': time_phase_prod,
        'time_phase_shipments': time_phase_ship
    }
    
    # Build master dataset
    result = build_master_dataset(data)
    
    print(f"\nResult shape: {result.shape}")
    print(f"Columns: {list(result.columns)}")
    print(f"\nFirst row summary:")
    print(f"  Style: {result.iloc[0]['Style']}")
    print(f"  AsgQty: {result.iloc[0].get('AsgQty', 'N/A')}")
    print(f"  ReservedQty: {result.iloc[0].get('ReservedQty', 'N/A')}")
    print(f"  B/O: {result.iloc[0].get('B/O', 'N/A')}")
    print(f"  OnHand: {result.iloc[0].get('OnHand', 'N/A')}")
    
    # Verify calculations
    # A100: AsgQty should be 500, ReservedQty 200, B/O 1000 (10 rolls * 100), OnHand 250 (100+150)
    a100_row = result[result['Style'] == 'A100'].iloc[0]
    assert a100_row['AsgQty'] == 500, f"A100 AsgQty should be 500, got {a100_row['AsgQty']}"
    assert a100_row['ReservedQty'] == 200, f"A100 ReservedQty should be 200, got {a100_row['ReservedQty']}"
    assert a100_row['B/O'] == 1000, f"A100 B/O should be 1000 (10*100), got {a100_row['B/O']}"
    assert a100_row['OnHand'] == 250, f"A100 OnHand should be 250, got {a100_row['OnHand']}"
    
    # A300: B/O should be 5 (5 LF, not rolls), OnHand 0
    a300_row = result[result['Style'] == 'A300'].iloc[0]
    assert a300_row['B/O'] == 5, f"A300 B/O should be 5, got {a300_row['B/O']}"
    assert a300_row['OnHand'] == 0, f"A300 OnHand should be 0, got {a300_row['OnHand']}"
    
    print("\n✓ Master dataset build test passed!")
    return True

def test_full_integration():
    """Test complete flow with time-phased inventory"""
    print("\n" + "=" * 70)
    print("Test 4: Full Integration Test")
    print("=" * 70)
    
    # Simple dataset
    df = pd.DataFrame({
        'Style': ['TEST'],
        'Color': ['RED'],
        'Size': ['12X12'],
        'Back': ['J'],
        'OnHand': [1000],
        'FC W 01': [100], 'FC W 02': [100], 'FC W 03': [100], 'FC W 04': [100],
        'FC W 05': [100], 'FC W 06': [100], 'FC W 07': [100], 'FC W 08': [100],
        'FC W 09': [100], 'FC W 10': [100], 'FC W 11': [100], 'FC W 12': [100],
        'PD W 01': [150], 'PD W 02': [150], 'PD W 03': [150], 'PD W 04': [150],
        'PD W 05': [150], 'PD W 06': [150], 'PD W 07': [150], 'PD W 08': [150],
        'PD W 09': [150], 'PD W 10': [150], 'PD W 11': [150], 'PD W 12': [150],
        'SH W 01': [25], 'SH W 02': [25], 'SH W 03': [25], 'SH W 04': [25],
        'SH W 05': [25], 'SH W 06': [25], 'SH W 07': [25], 'SH W 08': [25],
        'SH W 09': [25], 'SH W 10': [25], 'SH W 11': [25], 'SH W 12': [25],
    })
    
    result = add_time_phased_inventory(df)
    
    print(f"\nResults for TEST product:")
    print(f"  Starting OnHand: {result.iloc[0]['OnHand']}")
    print(f"  Net per week: -100 (FC) +150 (PD) -25 (SH) = +25")
    print(f"\n  Week projections:")
    for i in range(1, 13):
        week_col = f'Week {i:02d}'
        print(f"    {week_col}: {result.iloc[0][week_col]:.2f}")
    
    # Week 1 should be 1025 (1000 + 25)
    assert result.iloc[0]['Week 01'] == 1025, f"Week 01 should be 1025"
    # Week 12 should be 1300 (1000 + 25*12)
    assert result.iloc[0]['Week 12'] == 1300, f"Week 12 should be 1300"
    
    print("\n✓ Full integration test passed!")
    return True

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PHASE 4 CONVERTER TESTS - Mock Data Validation")
    print("=" * 70 + "\n")
    
    tests = [
        test_time_phased_inventory_calculation,
        test_depletion_scenario,
        test_master_dataset_build,
        test_full_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except AssertionError as e:
            print(f"\n✗ Test failed: {e}")
            results.append((test.__name__, False))
        except Exception as e:
            print(f"\n✗ Test error: {e}")
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print("=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)

if __name__ == "__main__":
    main()
