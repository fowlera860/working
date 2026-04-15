"""
WIP yarn inventory query for Yarn Cycle Planner.
Uses CAMSY (SQL Server) connection and exports a CSV for use in planning.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_inventory_query() -> str:
    """Build the WIP yarn inventory query for CAMSY."""
    return """
        SELECT
            Y1YNID,
            Y1YCLR,
            Y1LOT#,
            SUM(Y1CNES) as Y1CNES,
            SUM(Y1NWGT) as Y1NWGT,
            Y1WHSE

        FROM DATA.YAP010
        WHERE
            Y1ACT = 0
            AND Y1WHSE IN ('R1', 'R2', 'R3', 'R7', 'E1')
            AND Y1LOC <> 'WASTE'
        GROUP BY
            Y1YNID,
            Y1YCLR,
            Y1LOT#,
            Y1WHSE
    """


def main() -> None:
    config = load_config()
    paths = config["paths"]
    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    camsy_cfg = config.get("databases", {}).get("CAMSY")
    if not camsy_cfg:
        raise ValueError("Missing databases.CAMSY configuration")

    connection_string = build_connection_string(camsy_cfg)
    query = build_inventory_query()

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    fixed_output_path = export_folder / "WIP Yarn Inventory.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"WIP Yarn Inventory_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"WIP yarn inventory rows: {len(df)}")
    print(f"WIP yarn inventory export: {output_path}")


if __name__ == "__main__":
    main()
