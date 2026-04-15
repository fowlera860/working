"""
Finished yarn inventory query for Yarn Cycle Planner.
Pulls from CAMS (SQL Server) and exports a CSV for use in planning.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_inventory_query() -> str:
    """Build the finished yarn inventory query for CAMS."""
    return """
        SELECT
            Y1TYPE,
            Y1YCLR,
            Y1LOT#,
            SUM(Y1CNES) as Y1CNES,
            SUM(Y1NWGT) as Y1NWGT,
            Y1WHSE

        FROM DATA.YAP010
        WHERE
            Y1QLTY = 1
            AND Y1ACT = 0
            AND Y1WHSE in( 'E1')
        GROUP BY
            Y1TYPE,
            Y1YCLR,
            Y1LOT#,
            Y1WHSE
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
    query = build_inventory_query()

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    fixed_output_path = export_folder / "FIN Yarn Inventory.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"FIN Yarn Inventory_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"FIN yarn inventory rows: {len(df)}")
    print(f"FIN yarn inventory export: {output_path}")


if __name__ == "__main__":
    main()
