"""
Yarn Blend Cross-Reference converter for Yarn Cycle Planner.

Queries DATA.FIP027 to identify finished yarn → component yarn blend
relationships (e.g. a yarn made of multiple components at given percentages).

Only rows where BOTH the finished yarn (FYFTYP/FYFCLR) AND the component yarn
(FYCTYP/FYCCLR) exist in YarnAlts are retained — so the output is limited to
pairs that are actively planned.

Output: Yarn Blend XRef.csv
  FinType | FinColor | CompType | CompColor | Pct
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_blend_xref_query(yarn_types: list) -> str:
    """
    Pull FIP027 rows where both the finished and component yarn types are
    in YarnAlts.  The (type, color) pair filter is applied in Python after
    the query so the SQL stays simple and avoids excessively long IN lists.
    """
    if not yarn_types:
        raise ValueError("yarn_types list is empty — no YarnAlts data available")

    types_sql = ", ".join(f"'{t}'" for t in yarn_types)

    return f"""
        SELECT
            RTRIM(CAST(FYFTYP AS VARCHAR(20))) AS FinType,
            RTRIM(CAST(FYFCLR AS VARCHAR(20))) AS FinColor,
            RTRIM(CAST(FYCTYP AS VARCHAR(20))) AS CompType,
            RTRIM(CAST(FYCCLR AS VARCHAR(20))) AS CompColor,
            FYCPCT AS Pct
        FROM DATA.FIP027
        WHERE FYFTYP IN ({types_sql})
          AND FYCTYP IN ({types_sql})
    """


def main() -> None:
    config = load_config()
    paths = config["paths"]
    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    yarn_alts_path = Path(paths["yarn_alts_xlsx"])
    if not yarn_alts_path.exists():
        raise FileNotFoundError(f"Yarn Alts file not found: {yarn_alts_path}")

    yarn_alts_sheet = config.get("excel_sheets", {}).get("yarn_alts_sheet", "YarnAlts")
    yarn_alts_df = pd.read_excel(yarn_alts_path, sheet_name=yarn_alts_sheet, dtype=str)
    yarn_alts_df["YarnType"] = yarn_alts_df["YarnType"].str.strip()
    yarn_alts_df["YarnColor"] = yarn_alts_df["YarnColor"].str.strip()

    yarn_types = list(yarn_alts_df["YarnType"].dropna().unique())
    if not yarn_types:
        raise ValueError("No yarn types found in YarnAlts")

    cams_cfg = config.get("databases", {}).get("CAMS")
    if not cams_cfg:
        raise ValueError("Missing databases.CAMS configuration")

    connection_string = build_connection_string(cams_cfg)
    query = build_blend_xref_query(yarn_types)

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    for col in ["FinType", "FinColor", "CompType", "CompColor"]:
        df[col] = df[col].astype(str).str.strip()
    df["Pct"] = pd.to_numeric(df["Pct"], errors="coerce").fillna(0)

    print(f"  FIP027 rows returned (pre-filter): {len(df)}")

    # Filter: both finished and component yarn must be a known (type, color) pair in YarnAlts.
    # Use inner merges so no temporary columns are left in the output.
    ya = yarn_alts_df[["YarnType", "YarnColor"]].drop_duplicates()

    df = df.merge(
        ya.rename(columns={"YarnType": "FinType", "YarnColor": "FinColor"}),
        on=["FinType", "FinColor"],
        how="inner",
    )
    df = df.merge(
        ya.rename(columns={"YarnType": "CompType", "YarnColor": "CompColor"}),
        on=["CompType", "CompColor"],
        how="inner",
    )

    print(f"  Blend xref rows after YarnAlts filter: {len(df)}")

    if not df.empty:
        print("\n  Sample blend relationships:")
        print(
            df[["FinType", "FinColor", "CompType", "CompColor", "Pct"]]
            .head(10)
            .to_string(index=False)
        )

    fixed_output_path = export_folder / "Yarn Blend XRef.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"Yarn Blend XRef_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"\nYarn Blend XRef rows: {len(df)}")
    print(f"Yarn Blend XRef export: {output_path}")


if __name__ == "__main__":
    main()
