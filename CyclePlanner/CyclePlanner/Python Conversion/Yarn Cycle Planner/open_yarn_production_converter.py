"""
Open yarn production query for Yarn Cycle Planner.
Pulls from CAMSY (SQL Server) and exports a CSV for use in planning.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_open_yarn_production_query() -> str:
    """Build the open yarn production query for CAMSY."""
    return """
        SELECT
            Y7ORD#,
            Y7LNE#,
            Y7PCDE,
            Y7YNID,
            Y7YCLR,
            Y7LBSC,
            Y7LBPR,
            Y7ISSD,
            Y7MCH#,
            Y7LOT#,
            Y7IFLG,
            Y7SCJL + 366 as Y7SCJL

        FROM data.WYP070
        WHERE
            Y7ACT = 0
            AND Y7CJUL = 0
            AND Y7WHSE = 'R1'
            AND Y7CFLG <> 'Y'
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
    query = build_open_yarn_production_query()

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    fixed_output_path = export_folder / "Open Yarn Production.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"Open Yarn Production_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"Open yarn production rows: {len(df)}")
    print(f"Open yarn production export: {output_path}")


if __name__ == "__main__":
    main()
