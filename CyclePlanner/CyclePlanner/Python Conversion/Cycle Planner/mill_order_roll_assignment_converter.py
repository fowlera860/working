"""
MillOrderRollAssignment.pq conversion to Python
Fetches roll assignment data from CAMS database
"""

import pandas as pd
import pyodbc
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    build_group_filter_cte,
    export_with_fallback,
    ensure_export_folder
)

def build_mill_order_roll_assignment_query(planning_groups_df: pd.DataFrame) -> str:
    """Build the SQL query for roll assignments"""
    
    cte = build_group_filter_cte(planning_groups_df)
    
    query = cte + """
SELECT 
    FIP010.F1STYL AS Style,
    FIP010.F1CLR AS Color,
    FIP010.F1SIZE AS Size,
    FIP010.F1BACK AS Back,
    FIP010.F1AORD AS OrdNum,
    FIP010.F1ALNE AS OrdLine,
    FIP010.F1BLTF AS Qty,
    OPP010.O1PJUL AS PromJulian

FROM CAMS.DATA.FIP010 FIP010

LEFT OUTER JOIN CAMS.DATA.OPP010 OPP010
    ON OPP010.O1ORD# = FIP010.F1AORD
    AND OPP010.O1LINE = FIP010.F1ALNE

WHERE 
    FIP010.F1ACT < 7
    AND FIP010.F1AORD <> 0
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

def fetch_mill_order_roll_assignment(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fetch roll assignments from database"""
    try:
        db_server = config['database']['server']
        db_name = config['database']['database']
        
        connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={db_server};Database={db_name};Trusted_Connection=yes;"
        
        query = build_mill_order_roll_assignment_query(planning_groups_df)
        
        with pyodbc.connect(connection_string) as conn:
            df = pd.read_sql(query, conn)
        
        # Convert Julian date to datetime (Power Query adds +366 then casts to date)
        def julian_to_date(val):
            if pd.isna(val):
                return pd.NaT
            try:
                return pd.to_datetime('1899-12-31') + pd.to_timedelta(int(val) + 366, unit='D')
            except Exception:
                return pd.NaT
        
        if 'PromJulian' in df.columns:
            df['PromDt'] = df['PromJulian'].apply(julian_to_date).dt.date
        
        df['Src'] = 'Roll Reserve'
        
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
    
    # Create output paths
    fixed_output_path = export_folder / "mill_orders_roll_assignment.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"mill_orders_roll_assignment_{timestamp}.csv"
    
    print("=" * 60)
    print("Mill Order Roll Assignment Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch roll assignments
    print("Fetching roll assignments from database...")
    assignments_df = fetch_mill_order_roll_assignment(planning_groups_df, config)
    
    if assignments_df.empty:
        print("No data returned from database or connection failed")
        return
    
    print(f"Retrieved {len(assignments_df)} roll assignments")
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return
    
    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        assignments_df,
        fixed_output_path,
        timestamped_output_path
    )
    
    if not success:
        return
    
    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(assignments_df)}")
    print("\nFirst few rows:")
    print(assignments_df.head(10))
    print("\nColumn info:")
    print(assignments_df.dtypes)

if __name__ == "__main__":
    main()
