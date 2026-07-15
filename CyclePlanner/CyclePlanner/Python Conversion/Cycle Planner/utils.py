"""
Shared utilities for CyclePlanner converters
"""

import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple

def get_base_path():
    """
    Get the base path for the application.
    When running as PyInstaller exe, uses the exe's directory.
    Otherwise uses the script's directory.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use the exe's directory, not temp
        return Path(sys.executable).parent
    else:
        # Running as normal Python script
        return Path(__file__).parent

def load_config(config_path: str = None) -> dict:
    """Load configuration from config.json"""
    if config_path is None:
        base_path = get_base_path()
        config_path = base_path / "config.json"
        
        # If not found, try current working directory
        if not Path(config_path).exists():
            print(f"  ⚠ config.json not found at {config_path}, falling back to cwd: {Path.cwd()}")
            config_path = Path.cwd() / "config.json"
    
    print(f"  Loading config from: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    run_sizes = config.get('default_run_sizes', {})
    if run_sizes:
        print(f"  Run size tiers loaded: {list(run_sizes.keys())}")
    else:
        print(f"  ⚠ No default_run_sizes found in config!")
    return config

def load_planning_groups(planning_groups_path: str, sheet_name: str = "Planning_Groups") -> pd.DataFrame:
    """Load planning groups from Excel file with error handling"""
    try:
        # Force key columns to load as strings to preserve leading zeros
        dtype_dict = {'Style': 'string', 'Color': 'string', 'Size': 'string', 'Back': 'string'}
        df = pd.read_excel(planning_groups_path, sheet_name=sheet_name, dtype=dtype_dict)
        for col in ['PlanGroup', 'ColorGroup']:
            if col in df.columns:
                df[col] = df[col].str.strip()
        return df
    except ValueError as e:
        # Sheet name not found - show available sheets
        print(f"Error: {e}")
        print(f"\nAvailable sheets in {planning_groups_path}:")
        try:
            xl_file = pd.ExcelFile(planning_groups_path)
            for sheet in xl_file.sheet_names:
                print(f"  - {sheet}")
            print(f"\nPlease update config.json with the correct sheet name.")
        except Exception as inner_e:
            print(f"Could not read Excel file: {inner_e}")
        raise

def build_group_filter_cte(planning_groups_df: pd.DataFrame) -> str:
    """
    Build the SQL CTE VALUES clause from Planning_Groups DataFrame
    This creates a FilterList CTE used in all database queries
    Expects columns: Style, Color, Size, Back, PlanGroup, ColorGroup
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
    
    cte = f"""WITH FilterList AS (
    SELECT *
    FROM (VALUES
{values_block}
    ) AS v(style, color, size, back, planningGroup, colorGroup)
)"""
    return cte

def get_weeks_out(prom_date) -> int:
    """
    Calculate weeks from current week to promise date
    Current week = Sunday of current week
    Returns 1 if date is in past or current week
    """
    if pd.isna(prom_date):
        return 1
    
    today = datetime.now().date()
    # Sunday is day 6 in weekday(), so add 1 to get to Sunday
    current_week_sunday = today - timedelta(days=today.weekday() + 1)
    
    # Convert prom_date to date if it's a datetime
    if isinstance(prom_date, pd.Timestamp):
        prom_date = prom_date.date()
    
    weeks_diff = (prom_date - current_week_sunday).days // 7
    return 1 if weeks_diff <= 0 else weeks_diff

def pivot_to_weeks(
    df: pd.DataFrame,
    value_col: str,
    weeks: int = 20,
    prefix: str = "",
    key_cols: list[str] = None
) -> pd.DataFrame:
    """
    Pivot data into time-phased week columns
    
    Parameters:
    - df: DataFrame with 'WeeksOut' column and value_col to pivot
    - value_col: Column to aggregate (sum)
    - weeks: Number of weeks (1-20)
    - prefix: Prefix for week columns (e.g., "PD W ", "SH W ")
    
    - key_cols: Key columns used for row identity (default Style, Color, Size, Back)

    Returns: Pivoted DataFrame with columns: key_cols + W 01...W XX
    """
    if key_cols is None:
        key_cols = ['Style', 'Color', 'Size', 'Back']

    # Keep only needed columns
    needed_cols = key_cols + ['WeeksOut', value_col]
    df = df[[col for col in needed_cols if col in df.columns]]
    
    # Filter to weeks 1-N
    df = df[(df['WeeksOut'] >= 1) & (df['WeeksOut'] <= weeks)]
    
    # Create dummy rows for all weeks with 0 values
    dummy_rows = []
    for week in range(1, weeks + 1):
        row = {col: 0 for col in key_cols}
        row['WeeksOut'] = week
        row[value_col] = 0
        dummy_rows.append(row)
    dummy_df = pd.DataFrame(dummy_rows)
    
    # Combine real data with dummy rows
    combined = pd.concat([df, dummy_df], ignore_index=True)
    
    # Transform WeeksOut to text format
    combined['WeeksOut'] = combined['WeeksOut'].apply(
        lambda x: f"{prefix}W {str(int(x)).zfill(2)}"
    )
    
    # Pivot table
    pivoted = combined.pivot_table(
        index=key_cols,
        columns='WeeksOut',
        values=value_col,
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Create list of week columns in order
    week_cols = [f"{prefix}W {str(i).zfill(2)}" for i in range(1, weeks + 1)]
    
    # Reorder columns: key cols first, then weeks
    final_cols = key_cols + week_cols
    pivoted = pivoted[[col for col in final_cols if col in pivoted.columns]]
    
    # Filter out dummy rows (where the first key column is 0)
    first_key_col = key_cols[0]
    pivoted = pivoted[pivoted[first_key_col] != 0]
    
    return pivoted.reset_index(drop=True)

def export_with_fallback(df: pd.DataFrame, fixed_path: Path, timestamped_path: Path) -> Tuple[Path, bool]:
    """
    Export DataFrame to CSV with fallback
    Tries fixed path first, falls back to timestamped if locked
    
    Returns: (output_path, success_flag)
    """
    try:
        df.to_csv(fixed_path, index=False)
        return (fixed_path, True)
    except Exception as e:
        print(f"Warning: Could not write to {fixed_path}: {e}")
        print(f"Falling back to timestamped filename...")
        try:
            df.to_csv(timestamped_path, index=False)
            return (timestamped_path, True)
        except Exception as e2:
            print(f"Error: Failed to write CSV to both locations:")
            print(f"  {fixed_path}")
            print(f"  {timestamped_path}")
            print(f"Error: {e2}")
            return (None, False)

def ensure_export_folder(export_folder: Path) -> bool:
    """Ensure export folder exists"""
    try:
        export_folder.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating export folder {export_folder}: {e}")
        return False
