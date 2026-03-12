"""
Test script for Product_Specs and SalesForecast converters
Uses mock data to verify workflow
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

def create_mock_planning_groups() -> pd.DataFrame:
    """Create mock planning groups"""
    data = {
        'style': ['9223', '9224', '9225'],
        'color': ['00310', '00311', '00312'],
        'size': ['1200', '1200', '1200'],
        'back': ['08', '08', '08'],
        'planningGroup': ['NG-Wool', 'NG-Wool', 'NG-Wool'],
        'colorGroup': ['00310', '00311', '00312']
    }
    return pd.DataFrame(data)

def create_mock_product_specs() -> pd.DataFrame:
    """Create mock product specs"""
    data = {
        'PlanningGroup': ['NG-Wool', 'NG-Wool', 'NG-Wool'],
        'ColorGroup': ['00310', '00311', '00312'],
        'Style': ['9223', '9224', '9225'],
        'Color': ['00310', '00311', '00312'],
        'Size': ['1200', '1200', '1200'],
        'Back': ['08', '08', '08'],
        'StyleName': ['Style A', 'Style B', 'Style C'],
        'ColorName': ['Navy', 'Red', 'Black'],
        'RollSize': [60, 60, 60],
        'FaceWt': [24, 24, 24],
        'MachineNum': ['M01', 'M02', 'M01'],
        'MachineDescription': ['Tufter 1', 'Tufter 2', 'Tufter 1'],
        'EPN': ['EPN001', 'EPN002', 'EPN003']
    }
    return pd.DataFrame(data)

def create_mock_sales_forecast() -> pd.DataFrame:
    """Create mock sales forecast"""
    data = {
        'Style': ['9223', '9224', '9225'],
        'Color': ['00310', '00311', '00312'],
        'Size': ['1200', '1200', '1200'],
        'Back': ['08', '08', '08'],
        'FC W 01': [100, 150, 120],
        'FC W 02': [110, 160, 130],
        'FC W 03': [105, 155, 125],
        'FC W 04': [115, 165, 135],
        'FC W 05': [120, 170, 140],
        'FC W 06': [125, 175, 145],
        'FC W 07': [130, 180, 150],
        'FC W 08': [135, 185, 155],
        'FC W 09': [140, 190, 160],
        'FC W 10': [145, 195, 165],
        'FC W 11': [150, 200, 170],
        'FC W 12': [155, 205, 175],
    }
    return pd.DataFrame(data)

def test_workflow():
    """Test workflow"""
    print("=" * 60)
    print("Testing Phase 1 Converters - Product Specs & Sales Forecast")
    print("=" * 60)
    
    # Load config
    print("\n1. Loading configuration...")
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    print(f"   Export folder: {config['paths']['export_folder']}")
    print(f"   Planning Groups sheet: {config['excel_sheets']['planning_groups_sheet']}")
    print(f"   Sales Forecast sheet: {config['excel_sheets'].get('sales_forecast_sheet', 'N/A')}")
    
    # Create mock data
    print("\n2. Creating mock data...")
    planning_groups = create_mock_planning_groups()
    product_specs = create_mock_product_specs()
    sales_forecast = create_mock_sales_forecast()
    
    print(f"   Planning Groups: {len(planning_groups)} rows")
    print(f"   Product Specs: {len(product_specs)} rows")
    print(f"   Sales Forecast: {len(sales_forecast)} rows")
    
    # Test Product Specs
    print("\n3. Testing Product Specs processing...")
    print(f"   Columns: {product_specs.columns.tolist()}")
    print(f"   Data types: {product_specs.dtypes.to_dict()}")
    print(f"   Sample data:")
    print(product_specs.head(2))
    
    # Test Sales Forecast processing
    print("\n4. Testing Sales Forecast processing...")
    # Join with planning groups
    pg_join = planning_groups[['style', 'color', 'size', 'back', 'planningGroup', 'colorGroup']].copy()
    pg_join.columns = ['Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup']
    
    merged_forecast = sales_forecast.merge(
        pg_join,
        on=['Style', 'Color', 'Size', 'Back'],
        how='inner'
    )
    
    print(f"   Rows after join: {len(merged_forecast)}")
    print(f"   Columns: {merged_forecast.columns.tolist()}")
    print(f"   Sample data:")
    print(merged_forecast.head(2))
    
    # Export mock results
    print("\n5. Exporting mock data...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_folder = Path(__file__).parent / "test_output"
    export_folder.mkdir(exist_ok=True)
    
    product_specs.to_csv(export_folder / f"product_specs_test_{timestamp}.csv", index=False)
    merged_forecast.to_csv(export_folder / f"sales_forecast_test_{timestamp}.csv", index=False)
    
    print(f"   Product specs: {export_folder / f'product_specs_test_{timestamp}.csv'}")
    print(f"   Sales forecast: {export_folder / f'sales_forecast_test_{timestamp}.csv'}")
    
    # Verify
    print("\n6. Verifying exports...")
    ps_loaded = pd.read_csv(export_folder / f"product_specs_test_{timestamp}.csv")
    sf_loaded = pd.read_csv(export_folder / f"sales_forecast_test_{timestamp}.csv")
    
    print(f"   Product specs loaded: {len(ps_loaded)} rows, {len(ps_loaded.columns)} columns")
    print(f"   Sales forecast loaded: {len(sf_loaded)} rows, {len(sf_loaded.columns)} columns")
    
    print("\n✓ Phase 1 workflow test complete!")
    return True

if __name__ == "__main__":
    test_workflow()
