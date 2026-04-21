"""
Yarn assignments query for Yarn Cycle Planner.
Identifies yarn assigned to carpet production from YAP060 and calculates
an adjustment representing the difference between what was issued and what
was scheduled/budgeted.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_yarn_assignments_query() -> str:
    """
    Build the yarn assignments query for CAMS — YAP060 rows assigned to E1 production.

    GREATEST() is not available in older SQL Server versions so we use an
    equivalent CASE WHEN expression instead.
    """
    return """
        WITH yap060_base AS (
            SELECT
                Y6LOT#,
                Y6TYPE,
                Y6YCLR,
                Y6ORD#,
                Y6SCHD,
                Y6SUSG,
                Y6ISSD,
                Y6RETN,
                Y6ISSD - CASE WHEN Y6SCHD > Y6SUSG THEN Y6SCHD ELSE Y6SUSG END AS BASE_ADJ
            FROM DATA.YAP060
            WHERE Y6ACT = 0
              AND Y6PRDC = 'E1'
        )
        SELECT
            Y6LOT#,
            Y6TYPE,
            Y6YCLR,
            Y6ORD#,
            Y6SCHD,
            Y6SUSG,
            Y6ISSD,
            Y6RETN,
            CASE
                WHEN BASE_ADJ < 0          THEN BASE_ADJ
                WHEN BASE_ADJ - Y6RETN < 0 THEN 0
                ELSE BASE_ADJ - Y6RETN
            END AS ADJUSTMENT
        FROM yap060_base
    """


def main() -> None:
    config = load_config()
    paths = config["paths"]
    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    cams_cfg = config.get("databases", {}).get("CAMS")
    if not cams_cfg:
        raise ValueError("Missing databases.CAMS configuration")

    connection_string = build_connection_string(cams_cfg)
    query = build_yarn_assignments_query()

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    fixed_output_path = export_folder / "yarn_assignments.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"yarn_assignments_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"Yarn assignments rows: {len(df)}")
    print(f"Yarn assignments export: {output_path}")


if __name__ == "__main__":
    main()
