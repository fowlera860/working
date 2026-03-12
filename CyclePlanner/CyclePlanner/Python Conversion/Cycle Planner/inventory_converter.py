"""
Inventory.pq conversion to Python
Converts Power Query logic to Python with CSV export
"""

import sys
import pandas as pd
import pyodbc
import json
from pathlib import Path
from datetime import datetime

def load_config(config_path: str = None) -> dict:
    """Load configuration from config.json"""
    if config_path is None:
        # Check if running as exe
        if getattr(sys, 'frozen', False):
            # Running as compiled exe - use exe's directory
            base_path = Path(sys.executable).parent
        else:
            # Running as script
            base_path = Path(__file__).parent
        
        config_path = base_path / "config.json"
        
        # If not found, try current working directory
        if not config_path.exists():
            config_path = Path.cwd() / "config.json"
    
    with open(config_path, 'r') as f:
        return json.load(f)

# Load Planning Groups from Excel
def load_planning_groups(planning_groups_path: str, sheet_name: str = "Planning_Groups") -> pd.DataFrame:
    """Load planning groups from Excel file"""
    try:
        # Force key columns to load as strings to preserve leading zeros
        dtype_dict = {'Style': 'string', 'Color': 'string', 'Size': 'string', 'Back': 'string'}
        df = pd.read_excel(planning_groups_path, sheet_name=sheet_name, dtype=dtype_dict)
        return df
    except ValueError as e:
        # Sheet name not found - show available sheets
        print(f"Error: {e}")
        print(f"\nAvailable sheets in {planning_groups_path}:")
        try:
            xl_file = pd.ExcelFile(planning_groups_path)
            for sheet in xl_file.sheet_names:
                print(f"  - {sheet}")
            print(f"\nPlease update config.json 'excel_sheets.planning_groups_sheet' with the correct sheet name.")
        except Exception as inner_e:
            print(f"Could not read Excel file: {inner_e}")
        raise

def build_filter_values(planning_groups_df: pd.DataFrame) -> str:
    """
    Build the VALUES clause for the SQL CTE
    Converts DataFrame rows to SQL VALUES format
    Expects columns in order: Style, Color, Size, Back, PlanGroup, ColorGroup
    """
    # Ensure columns are in the right order
    expected_cols = ['Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup']
    
    # Check if all expected columns exist
    missing_cols = [col for col in expected_cols if col not in planning_groups_df.columns]
    if missing_cols:
        raise ValueError(f"Planning Groups missing columns: {missing_cols}. Found: {planning_groups_df.columns.tolist()}")
    
    # Select only the needed columns in the right order
    df_ordered = planning_groups_df[expected_cols]
    
    rows = []
    for _, row in df_ordered.iterrows():
        # Create tuple of quoted values: ('9223','00310','1200','08','NG-Wool','00310')
        values = [str(val) for val in row]
        row_str = "('" + "','".join(values) + "')"
        rows.append(row_str)
    
    values_block = ",\n".join(rows)
    return values_block

def build_cte_query(planning_groups_df: pd.DataFrame, inv_roll_cutoff: float) -> str:
    """Build the complete SQL query with CTE"""
    
    values_block = build_filter_values(planning_groups_df)
    
    query = f"""
WITH FilterList AS (
    SELECT *
    FROM (VALUES
{values_block}
    ) AS v(style, color, size, back, planningGroup, colorGroup)
)
SELECT 
    FIP010.F1STYL AS Style,
    FIP010.F1CLR AS Color,
    FIP010.F1SIZE AS Size,
    FIP010.F1BACK AS Back,
    FIP010.F1ROLL AS RollNumber,
    FIP010.F1ALTF AS Feet,
    FIP010.F1DLOT AS DyeLot,
    FIP010.F1WHSE AS WH,
    FIP010.F1LOC AS Loc
FROM data.FIP010 FIP010
WHERE 
    F1ACT = 0
    AND F1QLTY = 1
    AND FIP010.F1ALTF > 0
    AND FIP010.F1SFLG = ''
    AND FIP010.F1ALTF > {inv_roll_cutoff}
    AND EXISTS (
        SELECT 1
        FROM FilterList f
        WHERE 
            f.style = FIP010.F1STYL
            AND f.color = FIP010.F1CLR
            AND f.size = FIP010.F1SIZE
            AND f.back = FIP010.F1BACK
    )
"""
    return query

def fetch_inventory_data(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Fetch inventory data from SQL database
    """
    try:
        # Get config values
        db_server = config['database']['server']
        db_name = config['database']['database']
        inv_roll_cutoff = config['parameters']['inv_roll_cutoff']
        
        # Build connection string
        connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={db_server};Database={db_name};Trusted_Connection=yes;"
        
        # Build query
        query = build_cte_query(planning_groups_df, inv_roll_cutoff)
        
        # Connect and fetch data
        with pyodbc.connect(connection_string) as conn:
            df = pd.read_sql(query, conn)
        
        return df
    
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Returning empty DataFrame")
        return pd.DataFrame()

def main():
    """Main execution"""
    # Load configuration
    config = load_config()
    
    # Get paths from config
    planning_groups_path = Path(config['paths']['planning_groups_xlsx'])
    export_folder = Path(config['paths']['export_folder'])
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    
    # Create fixed output path (no timestamp)
    fixed_output_path = export_folder / "inventory.csv"
    
    # Create timestamp for fallback filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"inventory_{timestamp}.csv"
    
    print(f"Loading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch inventory data
    print("Fetching inventory data from database...")
    inventory_df = fetch_inventory_data(planning_groups_df, config)
    
    if inventory_df.empty:
        print("No data returned from database or connection failed")
        return
    
    # Ensure export folder exists
    export_folder.mkdir(parents=True, exist_ok=True)
    
    # Try to export to fixed path, fallback to timestamped if that fails
    try:
        inventory_df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
        print(f"Inventory data exported to: {output_path}")
    except Exception as e:
        print(f"Warning: Could not write to {fixed_output_path}: {e}")
        print(f"Falling back to timestamped filename...")
        try:
            inventory_df.to_csv(timestamped_output_path, index=False)
            output_path = timestamped_output_path
            print(f"Inventory data exported to: {output_path}")
        except Exception as e2:
            print(f"Error: Failed to write CSV to both locations:")
            print(f"  {fixed_output_path}")
            print(f"  {timestamped_output_path}")
            print(f"Error: {e2}")
            return
    
    print(f"Total rows: {len(inventory_df)}")
    print("\nFirst few rows:")
    print(inventory_df.head())

if __name__ == "__main__":
    main()
