"""
UnassignedMillOrders.pq conversion to Python
Fetches unassigned mill orders from CAMS database
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

def build_unassigned_mill_orders_query(planning_groups_df: pd.DataFrame) -> str:
    """Build the SQL query for unassigned mill orders"""
    
    cte = build_group_filter_cte(planning_groups_df)
    
    query = cte + """
SELECT 
    OPP010.O1ISTY AS Style,
    OPP010.O1ICLR AS Color,
    OPP010.O1ISZE AS Size,
    OPP010.O1IBK AS Back,
    OPP010.O1ORD# AS OrdNum,
    OPP010.O1LINE AS OrdLine,
    OPP010.O1OQTY AS Qty,
    OPP010.O1OQUM AS UOM,
    OPP010.O1PJUL AS PromJulian

FROM CAMS.DATA.OPP010 OPP010

WHERE 
    OPP010.O1CNCD = 0
    AND OPP010.O1OCJL = 0
    AND OPP010.O1AQTY = 0
    AND OPP010.O1AJUL = 0
    AND EXISTS (
        SELECT 1
        FROM FilterList f
        WHERE 
            f.style = OPP010.O1ISTY
            AND f.color = OPP010.O1ICLR
            AND f.size = OPP010.O1ISZE
            AND f.back = OPP010.O1IBK
    )
    AND NOT EXISTS (
        SELECT 1
        FROM CAMS.DATA.PRP010 PRP010
        WHERE
            OPP010.O1ORD# = PRP010.PRORD#
            AND OPP010.O1LINE = PRP010.PROLNE
    )
"""
    return query

def fetch_unassigned_mill_orders(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fetch unassigned mill orders from database"""
    try:
        db_server = config['database']['server']
        db_name = config['database']['database']
        
        connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={db_server};Database={db_name};Trusted_Connection=yes;"
        
        query = build_unassigned_mill_orders_query(planning_groups_df)
        
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
        
        # Add source column
        df['Src'] = 'Unassigned'
        
        # Note: In the original Power Query, UnassignedMillOrders joins with Product_Specs
        # to get RollSize and calculate LF (Linear Feet)
        # This is handled in the combined MillOrders converter
        
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
    fixed_output_path = export_folder / "mill_orders_unassigned.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"mill_orders_unassigned_{timestamp}.csv"
    
    print("=" * 60)
    print("Unassigned Mill Orders Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch unassigned mill orders
    print("Fetching unassigned mill orders from database...")
    unassigned_df = fetch_unassigned_mill_orders(planning_groups_df, config)
    
    if unassigned_df.empty:
        print("No data returned from database or connection failed")
        return
    
    print(f"Retrieved {len(unassigned_df)} unassigned mill orders")
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return
    
    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        unassigned_df,
        fixed_output_path,
        timestamped_output_path
    )
    
    if not success:
        return
    
    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(unassigned_df)}")
    print("\nFirst few rows:")
    print(unassigned_df.head(10))
    print("\nColumn info:")
    print(unassigned_df.dtypes)

if __name__ == "__main__":
    main()
