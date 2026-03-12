"""
SalesForecast.pq conversion to Python
Loads sales forecast from Excel and joins with Planning_Groups
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    export_with_fallback,
    ensure_export_folder
)


def clean_key_value(value):
    """Convert keys to clean strings: trim whitespace, remove .0 suffixes."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def normalize_keys(df: pd.DataFrame, template_lengths: dict | None = None) -> pd.DataFrame:
    """Normalize join keys to strings (trim whitespace, remove .0 suffixes)."""
    key_cols = ['Style', 'Color', 'Size', 'Back']
    for col in key_cols:
        if col in df.columns:
            df[col] = df[col].map(clean_key_value).astype('string')
    return df

def load_sales_forecast_excel(sales_forecast_path: str, sheet_name: str = "SalesForecast") -> pd.DataFrame:
    """Load sales forecast from Excel file"""
    try:
        # Force key columns to load as strings to preserve leading zeros
        dtype_dict = {'Style': 'string', 'Color': 'string', 'Size': 'string', 'Back': 'string'}
        df = pd.read_excel(sales_forecast_path, sheet_name=sheet_name, dtype=dtype_dict)
        return df
    except ValueError as e:
        print(f"Error: {e}")
        print(f"\nAvailable sheets in {sales_forecast_path}:")
        try:
            xl_file = pd.ExcelFile(sales_forecast_path)
            for sheet in xl_file.sheet_names:
                print(f"  - {sheet}")
            print(f"\nPlease update config.json 'excel_sheets.sales_forecast_sheet' with the correct sheet name.")
        except Exception as inner_e:
            print(f"Could not read Excel file: {inner_e}")
        raise

def process_sales_forecast(sales_forecast_df: pd.DataFrame, planning_groups_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process sales forecast data:
    1. Remove unwanted columns (weeks 1-26, totals, percentages)
    2. Keep only forecast columns (FC W 01-20)
    3. Convert column types
    4. Inner join with Planning_Groups
    5. Add planning group columns
    """
    
    # Columns to remove - all the non-forecast columns
    columns_to_remove = [
        'Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 
        'Week 7', 'Week 8', 'Week 9', 'Week 10', 'Week 11', 'Week 12', 
        'Week 13', 'Week 14', 'Week 15', 'Week 16', 'Week 17', 'Week 18', 
        'Week 19', 'Week 20', 'Week 21', 'Week 22', 'Week 23', 'Week 24', 
        'Week 25', 'Week 26', 'Weekly Total', 'Yards/Week', 'WeeksToUse', 
        'Adjustment', 'AdjustedSales', 'Sales/Week', 'Color Sales %', 'ForecastOrSales'
    ]
    
    # Remove columns that exist
    cols_to_drop = [col for col in columns_to_remove if col in sales_forecast_df.columns]
    df = sales_forecast_df.drop(columns=cols_to_drop)
    
    # Ensure forecast columns exist
    forecast_cols = [f'FC W {str(i).zfill(2)}' for i in range(1, 21)]
    for col in forecast_cols:
        if col not in df.columns:
            print(f"Warning: Forecast column '{col}' not found in Excel file")
    
    # Keep only columns that exist
    keep_cols = ['Style', 'Color', 'Size', 'Back'] + [col for col in forecast_cols if col in df.columns]
    df = df[keep_cols]
    
    # Convert types
    type_mapping = {
        'Style': 'string',
        'Color': 'string', 
        'Size': 'string',
        'Back': 'string'
    }
    
    # Add forecast columns as numeric
    for col in forecast_cols:
        if col in df.columns:
            type_mapping[col] = 'float64'
    
    df = df.astype(type_mapping)
    df = normalize_keys(df)
    
    # Prepare planning groups for join
    # Planning Groups has columns: Style, Color, Size, Back, PlanGroup, ColorGroup
    pg_join = planning_groups_df[['Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup']].copy()
    
    # Convert planning groups to same types for join
    pg_join = pg_join.astype({
        'Style': 'string',
        'Color': 'string',
        'Size': 'string', 
        'Back': 'string'
    })
    pg_join = normalize_keys(pg_join)
    
    # Inner join with Planning_Groups
    merged = df.merge(
        pg_join,
        on=['Style', 'Color', 'Size', 'Back'],
        how='inner'
    )
    unmatched_count = len(df) - len(merged)
    if unmatched_count > 0:
        print(f"Warning: {unmatched_count} rows from forecast did not match Planning_Groups after normalization")
        unmatched_sample = (
            df.merge(pg_join, on=['Style', 'Color', 'Size', 'Back'], how='left', indicator=True)
              .loc[lambda m: m['_merge'] == 'left_only', ['Style', 'Color', 'Size', 'Back']]
              .drop_duplicates()
              .head(10)
        )
        if not unmatched_sample.empty:
            print("Sample unmatched keys:")
            print(unmatched_sample.to_string(index=False))
    
    return merged

def main():
    """Main execution"""
    # Load configuration
    config = load_config()
    
    # Get paths from config
    planning_groups_path = Path(config['paths']['planning_groups_xlsx'])
    sales_forecast_path = Path(config['paths']['sales_forecast_xlsx'])
    export_folder = Path(config['paths']['export_folder'])
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    sales_forecast_sheet = config['excel_sheets'].get('sales_forecast_sheet', 'SalesForecast')
    
    # Create output paths
    fixed_output_path = export_folder / "sales_forecast.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"sales_forecast_{timestamp}.csv"
    
    print("=" * 60)
    print("Sales Forecast Converter")
    print("=" * 60)
    
    # Load planning groups
    print(f"\nLoading planning groups from: {planning_groups_path}")
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Load sales forecast
    print(f"\nLoading sales forecast from: {sales_forecast_path}")
    if not sales_forecast_path.exists():
        print(f"Error: Sales Forecast file not found at {sales_forecast_path}")
        return
    
    sales_forecast_df = load_sales_forecast_excel(str(sales_forecast_path), sales_forecast_sheet)
    print(f"Loaded {len(sales_forecast_df)} forecast rows")
    
    # Process forecast data
    print("Processing and joining forecast data...")
    processed_df = process_sales_forecast(sales_forecast_df, planning_groups_df)
    
    if processed_df.empty:
        print("No data matched between forecast and planning groups")
        return
    
    print(f"Processed {len(processed_df)} forecast rows")
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return
    
    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        processed_df,
        fixed_output_path,
        timestamped_output_path
    )
    
    if not success:
        return
    
    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(processed_df)}")
    print("\nFirst few rows:")
    print(processed_df.head(10))
    print("\nColumn info:")
    print(processed_df.dtypes)

if __name__ == "__main__":
    main()
