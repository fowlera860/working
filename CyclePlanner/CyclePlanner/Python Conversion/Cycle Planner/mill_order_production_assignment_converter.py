"""
MillOrderProductionAssignment.pq conversion to Python
Fetches production order assignments from CAMS database
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

def build_mill_order_production_assignment_query(planning_groups_df: pd.DataFrame) -> str:
    """Build the SQL query for production order assignments"""
    
    cte = build_group_filter_cte(planning_groups_df)
    
    query = cte + """
SELECT 
    PRP010.PRSTYL AS Style,
    PRP010.PRCLR AS Color,
    PRP010.PRSIZE AS Size,
    PRP010.PRBACK AS Back,
    PRP010.PRORD# AS OrdNum,
    PRP010.PROLNE AS OrdLine,
    PRP010.PRCTL# AS ProdOrder,
    PRP010.PRQTY AS AsgQty,
    PRP010.PRCJUL AS PromJulian,
    ISNULL(SUM(FIP010.F1BLTF), 0) AS RsvQty,
    CASE 
        WHEN PRP010.PRQTY - ISNULL(SUM(FIP010.F1BLTF), 0) < 0 THEN 0
        ELSE PRP010.PRQTY - ISNULL(SUM(FIP010.F1BLTF), 0)
    END AS PendingProd

FROM CAMS.DATA.PRP010 PRP010
LEFT OUTER JOIN CAMS.DATA.FIP010 FIP010
    ON FIP010.F1AORD = PRP010.PRORD#
    AND FIP010.F1ALNE = PRP010.PROLNE

WHERE 
    PRPRTF <> 'Y'
    AND EXISTS (
        SELECT 1
        FROM FilterList f
        WHERE 
            f.style = PRP010.PRSTYL
            AND f.color = PRP010.PRCLR
            AND f.size = PRP010.PRSIZE
            AND f.back = PRP010.PRBACK
    )
GROUP BY
    PRP010.PRSTYL,
    PRP010.PRCLR,
    PRP010.PRSIZE,
    PRP010.PRBACK,
    PRP010.PRORD#,
    PRP010.PROLNE,
    PRP010.PRCTL#,
    PRP010.PRQTY,
    PRP010.PRCJUL
"""
    return query

def fetch_mill_order_production_assignment(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fetch production order assignments from database"""
    try:
        db_server = config['database']['server']
        db_name = config['database']['database']
        
        connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={db_server};Database={db_name};Trusted_Connection=yes;"
        
        query = build_mill_order_production_assignment_query(planning_groups_df)
        
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
        
        df['Src'] = 'Production Assignment'
        
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
    fixed_output_path = export_folder / "mill_orders_production_assignment.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"mill_orders_production_assignment_{timestamp}.csv"
    
    print("=" * 60)
    print("Mill Order Production Assignment Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch production assignments
    print("Fetching production order assignments from database...")
    assignments_df = fetch_mill_order_production_assignment(planning_groups_df, config)
    
    if assignments_df.empty:
        print("No data returned from database or connection failed")
        return
    
    print(f"Retrieved {len(assignments_df)} production assignments")
    
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
