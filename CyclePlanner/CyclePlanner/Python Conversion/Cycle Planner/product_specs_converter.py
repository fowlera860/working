"""
Product_Specs.pq conversion to Python
Fetches product specifications from CAMS database
"""

import pandas as pd
import pyodbc
from pathlib import Path
from datetime import datetime
from utils import (
    load_config, 
    load_planning_groups, 
    export_with_fallback,
    ensure_export_folder
)


def _sql_escape(value) -> str:
    """Escape a value for safe inclusion in SQL string literals."""
    return str(value).replace("'", "''")


def build_product_specs_filter_cte(planning_groups_df: pd.DataFrame) -> str:
    """
    Build Product_Specs filter CTE, preserving original Style while carrying
    optional Tufting Spec Style for join-only overrides.
    """
    required_cols = ['Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup']
    missing_cols = [col for col in required_cols if col not in planning_groups_df.columns]
    if missing_cols:
        raise ValueError(f"Planning Groups missing columns: {missing_cols}. Found: {planning_groups_df.columns.tolist()}")

    override_col = "Tufting Spec Style"
    has_override_col = override_col in planning_groups_df.columns

    rows = []
    for _, row in planning_groups_df.iterrows():
        style = '' if pd.isna(row['Style']) else _sql_escape(row['Style'])
        color = '' if pd.isna(row['Color']) else _sql_escape(row['Color'])
        size = '' if pd.isna(row['Size']) else _sql_escape(row['Size'])
        back = '' if pd.isna(row['Back']) else _sql_escape(row['Back'])
        planning_group = '' if pd.isna(row['PlanGroup']) else _sql_escape(row['PlanGroup'])
        color_group = '' if pd.isna(row['ColorGroup']) else _sql_escape(row['ColorGroup'])

        if has_override_col and not pd.isna(row[override_col]):
            tufting_spec_style = _sql_escape(str(row[override_col]).strip())
        else:
            tufting_spec_style = ''

        rows.append(
            f"('{style}','{color}','{size}','{back}','{planning_group}','{color_group}','{tufting_spec_style}')"
        )

    values_block = ",\n".join(rows)
    return f"""WITH FilterList AS (
    SELECT *
    FROM (VALUES
{values_block}
    ) AS v(style, color, size, back, planningGroup, colorGroup, tuftingSpecStyle)
)"""

def build_product_specs_query(planning_groups_df: pd.DataFrame) -> str:
    """Build the SQL query for product specifications"""

    cte = build_product_specs_filter_cte(planning_groups_df)
    
    query = cte + """
SELECT DISTINCT
    f.planningGroup AS PlanningGroup,
    f.colorGroup AS ColorGroup,
    f.style AS Style,
    f.color AS Color,
    f.size AS Size,
    f.back AS Back,
    FIP020.F2SDSC AS StyleName,
    FIP020.F2CDSC AS ColorName,
    FIP020B.F2SLTH AS RollSize,
    FIP020B.F2DTYP AS DyeType,
    COALESCE(FIP715.F7WGHTC, FIP020B.F2FCWT) AS FaceWt,
    FIP715.F7CMCH AS MachineNum,
    GIP030.G3DESC AS MachineDescription,
    FIP715.F7EPN AS EPN
FROM data.FIP020 FIP020
INNER JOIN FilterList f
    ON FIP020.F2STYL = CASE
        WHEN LTRIM(RTRIM(ISNULL(f.tuftingSpecStyle, ''))) <> '' THEN f.tuftingSpecStyle
        ELSE f.style
    END
    AND FIP020.F2CLR = f.color
    AND FIP020.F2SIZE = f.size
    AND FIP020.F2BACK = f.back
INNER JOIN data.FIP020B FIP020B
    ON FIP020.F2STYL = FIP020B.F2STYL
    AND FIP020.F2CLR = FIP020B.F2CLR
    AND FIP020.F2SIZE = FIP020B.F2SIZE
    AND FIP020.F2BACK = FIP020B.F2BACK
LEFT OUTER JOIN data.FIP712 FIP712
    ON FIP020.F2STYL = FIP712.F7STYL
    AND FIP020.F2SIZE = FIP712.F7SIZE
    AND FIP712.F7MASTER = 'Y'
    AND FIP712.F7APPVD = 'Y'
    AND FIP712.F7PCODE = 'TFT'
LEFT OUTER JOIN data.FIP715 FIP715
    ON FIP020.F2STYL = FIP715.F7STYL
    AND FIP020.F2SIZE = FIP715.F7SIZE
    AND FIP712.F7SPEC# = FIP715.F7SPEC#
    AND FIP712.F7SPEC = FIP715.F7SPEC
LEFT OUTER JOIN data.GIP030 GIP030
    ON GIP030.G3MACH = FIP715.F7CMCH
ORDER BY 
    PlanningGroup,
    ColorGroup,
    Style,
    Color
"""
    return query


def reconcile_product_specs_keys(product_specs_df: pd.DataFrame, planning_groups_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure output keys match original Planning_Groups keys.
    Tufting Spec Style is only a lookup override, never an output key.
    """
    if product_specs_df.empty or planning_groups_df.empty:
        return product_specs_df

    required_cols = ['Style', 'Color', 'Size', 'Back', 'PlanGroup', 'ColorGroup']
    missing_cols = [col for col in required_cols if col not in planning_groups_df.columns]
    if missing_cols:
        return product_specs_df

    pg = planning_groups_df.copy()
    if 'Tufting Spec Style' in pg.columns:
        tufting = pg['Tufting Spec Style'].astype('string').fillna('').str.strip()
    else:
        tufting = pd.Series([''] * len(pg), index=pg.index, dtype='string')

    pg['EffectiveStyle'] = pg['Style'].astype('string')
    has_tufting = tufting != ''
    pg.loc[has_tufting, 'EffectiveStyle'] = tufting[has_tufting]

    key_cols = ['EffectiveStyle', 'Color', 'Size', 'Back']
    map_cols = key_cols + ['Style', 'PlanGroup', 'ColorGroup']
    pg_map = pg[map_cols].drop_duplicates(subset=key_cols, keep='first').rename(columns={
        'Style': 'OriginalStyle',
        'PlanGroup': 'OriginalPlanningGroup',
        'ColorGroup': 'OriginalColorGroup'
    })

    merged = product_specs_df.merge(
        pg_map,
        left_on=['Style', 'Color', 'Size', 'Back'],
        right_on=['EffectiveStyle', 'Color', 'Size', 'Back'],
        how='left'
    )

    if 'OriginalStyle' in merged.columns:
        merged['Style'] = merged['OriginalStyle'].fillna(merged['Style'])

    if 'OriginalPlanningGroup' in merged.columns:
        if 'PlanningGroup' in merged.columns:
            merged['PlanningGroup'] = merged['OriginalPlanningGroup'].fillna(merged['PlanningGroup'])
        else:
            merged['PlanningGroup'] = merged['OriginalPlanningGroup']

    if 'OriginalColorGroup' in merged.columns:
        if 'ColorGroup' in merged.columns:
            merged['ColorGroup'] = merged['OriginalColorGroup'].fillna(merged['ColorGroup'])
        else:
            merged['ColorGroup'] = merged['OriginalColorGroup']

    drop_cols = [
        'EffectiveStyle',
        'OriginalStyle',
        'OriginalPlanningGroup',
        'OriginalColorGroup'
    ]
    merged = merged.drop(columns=[col for col in drop_cols if col in merged.columns])

    return merged

def fetch_product_specs(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fetch product specs from database"""
    try:
        db_server = config['database']['server']
        db_name = config['database']['database']
        
        connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={db_server};Database={db_name};Trusted_Connection=yes;"
        
        query = build_product_specs_query(planning_groups_df)
        
        with pyodbc.connect(connection_string) as conn:
            df = pd.read_sql(query, conn)

        df = reconcile_product_specs_keys(df, planning_groups_df)
        
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
    fixed_output_path = export_folder / "product_specs.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"product_specs_{timestamp}.csv"
    
    print("=" * 60)
    print("Product Specs Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")
    
    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return False
    
    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")
    
    # Fetch product specs
    print("Fetching product specifications from database...")
    product_specs_df = fetch_product_specs(planning_groups_df, config)
    
    if product_specs_df.empty:
        print("No data returned from database or connection failed")
        return False
    
    print(f"Retrieved {len(product_specs_df)} product specifications")
    
    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return False
    
    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        product_specs_df, 
        fixed_output_path, 
        timestamped_output_path
    )
    
    if not success:
        return False
    
    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(product_specs_df)}")
    print("\nFirst few rows:")
    print(product_specs_df.head(10))
    print("\nColumn info:")
    print(product_specs_df.dtypes)
    return True

if __name__ == "__main__":
    main()
