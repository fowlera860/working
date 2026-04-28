"""
Pending yarn orders query for Yarn Cycle Planner.
Pulls from CAMS (SQL Server) and exports a CSV for use in planning.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from utils import load_config, ensure_export_folder, build_connection_string


def build_pending_yarn_orders_query() -> str:
    """Build the pending yarn orders query for CAMS."""
    return """
        SELECT
            Y8PO#,
            Y8TYPE,
            Y8YCLR,
            Y8LOT#,
            Y8WHSE,
            Y8VND#,
            Y8OWGT,
            Y8RWGT,
            CASE
                WHEN Y8OWGT - Y8RWGT > 0 THEN Y8OWGT - Y8RWGT
                ELSE 0
            END AS OrderBalance,
            Y8SJUL + 366 as Y8SJUL
        FROM DATA.YAP080
        WHERE
            Y8ACT = 0
            AND Y8WHSE in ('E1')

        UNION ALL

        SELECT
            A.Y7ORD#,
            A.Y7TYPE,
            A.Y7YCLR,
            A.Y7ORD#,
            NULL,
            NULL,
            A.Y7LBSC,
            A.Y7LBPR,
            A.Y7LBSC - A.Y7LBPR,
            A.Y7OJUL + 366
        FROM DATA.WYP070 AS A
        WHERE
            A.Y7WHSE = 'E1'
            AND A.Y7ACT = 0
            AND A.Y7PCDE = 'YPK'
            AND A.Y7LBSC > A.Y7LBPR * 1.2
            AND EXISTS (
                SELECT 1
                FROM DATA.WYP070 AS B
                WHERE
                    B.Y7ORD# = A.Y7ORD#
                    AND B.Y7PCDE = 'GBO'
                    AND B.Y7ACT = 0
            )
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
    query = build_pending_yarn_orders_query()

    with pyodbc.connect(connection_string) as conn:
        df = pd.read_sql(query, conn)

    # Convert Julian integer to calendar date (SQL already added +366, treat as OA date)
    def julian_to_date(val):
        try:
            return (pd.to_datetime('1899-12-31') + pd.to_timedelta(int(val), unit='D')).date()
        except Exception:
            return None

    if 'Y8SJUL' in df.columns:
        df['OrderDate'] = df['Y8SJUL'].apply(julian_to_date)

    fixed_output_path = export_folder / "Pending Yarn Orders.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"Pending Yarn Orders_{timestamp}.csv"

    try:
        df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"Pending yarn orders rows: {len(df)}")
    print(f"Pending yarn orders export: {output_path}")


if __name__ == "__main__":
    main()
