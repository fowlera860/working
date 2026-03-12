"""
YarnXRef.pq conversion to Python
Fetches yarn cross reference data from CAMS database
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

def build_yarnxref_query(planning_groups_df: pd.DataFrame) -> str:
    """Build the SQL query for yarn cross reference"""
    cte = build_group_filter_cte(planning_groups_df)

    query = cte + """
SELECT
    FIP025.FYSTYL AS Style,
    FIP025.FYCLR AS Color,
    FIP025.FYSIZE AS Size,
    FIP025.[FYALT#] AS [Alt#],
    FIP025.FYBEAM AS BeamGroup,
    FIP025.FYYSEQ AS Seq,
    FIP025.FYYNID AS YarnID,
    FIP025.FYTYPE AS YarnType,
    FIP025.FYYCLR AS YarnColor,
    FIP025.FYOZSY AS OzSY,
    FIP025.[FY#END] AS NumEnds,
    FIP025.FYYPCT AS Per,
    FIP025.FYBMYN AS Beamed
FROM data.FIP025 FIP025
WHERE
    FIP025.[FYALT#] = 0
    AND EXISTS (
        SELECT 1
        FROM FilterList f
        WHERE
            f.style = FIP025.FYSTYL
            AND (
                f.color = FIP025.FYCLR
                OR f.color = ''
            )
            AND f.size = FIP025.FYSIZE
    )
"""
    return query

def fetch_yarnxref(planning_groups_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fetch yarn cross reference data from database"""
    try:
        db_server = config['database']['server']
        db_name = config['database']['database']

        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={db_server};"
            f"Database={db_name};"
            "Trusted_Connection=yes;"
        )

        query = build_yarnxref_query(planning_groups_df)

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

    # Create output paths
    fixed_output_path = export_folder / "yarnxref.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"yarnxref_{timestamp}.csv"

    print("=" * 60)
    print("YarnXRef Converter")
    print("=" * 60)
    print(f"\nLoading planning groups from: {planning_groups_path}")

    # Load planning groups
    if not planning_groups_path.exists():
        print(f"Error: Planning Groups file not found at {planning_groups_path}")
        return

    planning_groups_df = load_planning_groups(str(planning_groups_path), planning_groups_sheet)
    print(f"Loaded {len(planning_groups_df)} planning groups")

    # Fetch yarn cross reference data
    print("Fetching yarn cross reference data from database...")
    yarnxref_df = fetch_yarnxref(planning_groups_df, config)

    if yarnxref_df.empty:
        print("No data returned from database or connection failed")
        return

    print(f"Retrieved {len(yarnxref_df)} yarn cross reference rows")

    # Ensure export folder exists
    if not ensure_export_folder(export_folder):
        return

    # Export to CSV with fallback
    output_path, success = export_with_fallback(
        yarnxref_df,
        fixed_output_path,
        timestamped_output_path
    )

    if not success:
        return

    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(yarnxref_df)}")
    print("\nFirst few rows:")
    print(yarnxref_df.head(10))
    print("\nColumn info:")
    print(yarnxref_df.dtypes)

if __name__ == "__main__":
    main()
