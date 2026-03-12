"""
Production Orders Converter
Extracts production order details from PPP010 table
Maps to TimePhaseProductionOrders.pq
"""

import sys
import pyodbc
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    load_planning_groups,
    get_weeks_out,
    export_with_fallback,
    ensure_export_folder
)

def build_production_orders_query(planning_groups_df: pd.DataFrame) -> str:
    """
    Build SQL query for production orders
    Uses PPP010 columns (PPSTYL, PPCLR, PPSIZE, PPBACK, PPCTL#, PPOQTY, PPJULN, PPPRJL, PPWHSE)
    Filters latest sequence per style/color/size/back via ROW_NUMBER
    Excludes completed orders (PPCOMP = 'Y')
    """
    filter_values = planning_groups_df[[
        'Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup'
    ]].drop_duplicates()

    def sql_escape(value) -> str:
        return str(value).replace("'", "''")
    
    values_clause = ", ".join([
        f"('{sql_escape(row['Style'])}', '{sql_escape(row['Color'])}', '{sql_escape(row['Size'])}', "
        f"'{sql_escape(row['Back'])}', '{sql_escape(row['PlanGroup'])}', '{sql_escape(row['ColorGroup'])}')"
        for _, row in filter_values.iterrows()
    ])
    
    group_filter_cte = f"""
    WITH FilterList AS (
        SELECT * FROM (VALUES
            {values_clause}
        ) AS v(style, color, size, back, planningGroup, colorGroup)
    ), SkuMapRaw AS (
        -- Always include base SKU from filter list
        SELECT
            FL.style AS PGSTYL,
            FL.color AS PGCLR,
            FL.size AS PGSIZE,
            FL.back AS PGBACK,
            FL.planningGroup,
            FL.colorGroup,
            FL.style AS MatchStyle,
            FL.color AS MatchColor,
            FL.size AS MatchSize
        FROM FilterList FL

        UNION ALL

        -- Include x-ref SKUs that production orders may use
        SELECT
            FL.style AS PGSTYL,
            FL.color AS PGCLR,
            FL.size AS PGSIZE,
            FL.back AS PGBACK,
            FL.planningGroup,
            FL.colorGroup,
            XR.FXOSTY AS MatchStyle,
            XR.FXOCLR AS MatchColor,
            XR.FXOSIZ AS MatchSize
        FROM FilterList FL
        INNER JOIN CAMS.DATA.FIP028 XR
            ON XR.FXSTYL = FL.style
            AND XR.FXCLR = FL.color
            AND XR.FXSIZE = FL.size
        WHERE LTRIM(RTRIM(COALESCE(XR.FXOSTY, ''))) <> ''
            AND LTRIM(RTRIM(COALESCE(XR.FXOCLR, ''))) <> ''
            AND LTRIM(RTRIM(COALESCE(XR.FXOSIZ, ''))) <> ''
    ), SkuMap AS (
        SELECT DISTINCT
            PGSTYL,
            PGCLR,
            PGSIZE,
            PGBACK,
            planningGroup,
            colorGroup,
            MatchStyle,
            MatchColor,
            MatchSize
        FROM SkuMapRaw
    ), Ranked AS (
        SELECT 
            PPSTYL, PPCLR, PPSIZE, PPBACK,
            PPCTL# AS ProdNum,
            PPOQTY AS FtOrdered,
            PPJULN AS ProdJulian,
            PPPRJL AS PromJulian,
            PPWHSE AS WH,
            PPSEQ# AS Seq,
            PPCOMP,
            ROW_NUMBER() OVER (
                PARTITION BY PPSTYL, PPCLR, PPSIZE, PPBACK
                ORDER BY PPSEQ# DESC
            ) AS rn
        FROM CAMS.DATA.PPP010
        WHERE PPCOMP <> 'Y'
    )
    SELECT
        SM.PGSTYL,
        SM.PGCLR,
        SM.PGSIZE,
        SM.PGBACK,
        R.PPSTYL AS Style,
        R.PPCLR AS Color,
        R.PPSIZE AS Size,
        R.PPBACK AS Back,
        R.ProdNum,
        R.FtOrdered,
        R.ProdJulian,
        R.PromJulian,
        R.WH,
        R.Seq
    FROM Ranked R
    INNER JOIN SkuMap SM
        ON R.PPSTYL = SM.MatchStyle
        AND R.PPCLR = SM.MatchColor
        AND R.PPSIZE = SM.MatchSize
        AND R.PPBACK = SM.PGBACK
    WHERE R.rn = 1
    ORDER BY SM.PGSTYL, SM.PGCLR, SM.PGSIZE, SM.PGBACK, R.PPSTYL, R.PPCLR, R.PPSIZE, R.PPBACK
    """
    
    sql = group_filter_cte
    return sql

def fetch_production_orders(planning_groups_df: pd.DataFrame) -> pd.DataFrame:
    """Fetch production orders from database"""
    config = load_config()
    
    try:
        sql = build_production_orders_query(planning_groups_df)
        
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={config['database']['server']};"
            f"Database={config['database']['database']};"
            f"Trusted_Connection=yes;"
        )
        
        with pyodbc.connect(conn_str) as conn:
            df = pd.read_sql(sql, conn)
        
        print(f"  Loaded {len(df)} production orders")
        return df
        
    except Exception as e:
        print(f"  Error fetching production orders: {e}")
        raise

def process_production_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Process production orders with calculations"""
    if df.empty:
        return df
    
    # Normalize quantity column name
    if 'FtOrdered' in df.columns:
        df = df.rename(columns={'FtOrdered': 'OrderQty'})
    
    # Convert Julian integer columns to dates (Power Query adds +366 then casts to date)
    def julian_to_date(val):
        if pd.isna(val):
            return pd.NaT
        try:
            # PowerQuery used +366 then cast to date; mimic by origin 1899-12-31
            return pd.to_datetime('1899-12-31') + pd.to_timedelta(int(val) + 366, unit='D')
        except Exception:
            return pd.NaT
    
    if 'ProdJulian' in df.columns:
        df['ProdDate'] = df['ProdJulian'].apply(julian_to_date)
    if 'PromJulian' in df.columns:
        df['PromiseDate'] = df['PromJulian'].apply(julian_to_date)
    
    # Calculate WeeksOut from PromiseDate
    if 'PromiseDate' in df.columns:
        df['WeeksOut'] = df['PromiseDate'].apply(get_weeks_out)
    
    return df

def main():
    """Main entry point"""
    print("  Loading configuration...")
    config = load_config()
    export_folder = Path(config['paths']['export_folder'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixed_output_path = export_folder / "production_orders.csv"
    timestamped_output_path = export_folder / f"production_orders_{timestamp}.csv"
    
    print("  Loading planning groups...")
    planning_groups_path = config['paths']['planning_groups_xlsx']
    planning_groups_sheet = config['excel_sheets']['planning_groups_sheet']
    planning_groups_path_obj = Path(planning_groups_path)
    if not planning_groups_path_obj.exists():
        print(f"  ⚠ Planning Groups file not found at {planning_groups_path}")
        print("  (This is expected in dev/test environments)")
        return
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    
    print("  Fetching production orders...")
    production_orders_df = fetch_production_orders(planning_groups_df)
    
    if not production_orders_df.empty:
        print("  Processing production orders...")
        production_orders_df = process_production_orders(production_orders_df)
        
        print("  Exporting to CSV...")
        ensure_export_folder(export_folder)
        output_path, ok = export_with_fallback(
            production_orders_df,
            fixed_output_path,
            timestamped_output_path
        )
        if ok and output_path is not None:
            print(f"  ✓ Exported to {output_path}")
        else:
            print("  ✗ Failed to export production_orders.csv")
    else:
        print("  ⚠ No production orders returned")

if __name__ == "__main__":
    main()
