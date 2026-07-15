"""
Yarn Production Cycle Planner Prebuild - SKU Level converter.

Merges YarnAlts with Open Yarn Production aggregated by YarnType/YarnColor.
Output columns start with the same 5 as the Yarn Cycle Planner prebuild:
  PlanningGroup | ColorGroup | YarnType | YarnColor | Supplier
followed by SKU-level production metrics.
"""

from pathlib import Path

import pandas as pd

from utils import load_config, ensure_export_folder


def main() -> None:
    config = load_config()
    paths = config["paths"]

    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    yarn_alts_path = Path(paths["yarn_alts_xlsx"])
    open_yarn_prod_path = export_folder / "Open Yarn Production.csv"

    if not yarn_alts_path.exists():
        raise FileNotFoundError(f"Yarn Alts file not found: {yarn_alts_path}")
    if not open_yarn_prod_path.exists():
        raise FileNotFoundError(
            f"Open Yarn Production.csv not found: {open_yarn_prod_path}\n"
            "Run the open yarn production converter first."
        )

    yarn_alts_sheet = config.get("excel_sheets", {}).get("yarn_alts_sheet", "YarnAlts")

    yarn_alts_df = pd.read_excel(yarn_alts_path, sheet_name=yarn_alts_sheet, dtype=str)
    open_prod_df = pd.read_csv(open_yarn_prod_path, dtype={"Y7YNID": str, "Y7YCLR": str})

    # Normalise key columns
    for col in ["YarnType", "YarnColor", "PlanningGroup", "ColorGroup"]:
        if col in yarn_alts_df.columns:
            yarn_alts_df[col] = yarn_alts_df[col].str.strip()

    open_prod_df["Y7YNID"] = open_prod_df["Y7YNID"].astype(str).str.strip()
    open_prod_df["Y7YCLR"] = open_prod_df["Y7YCLR"].astype(str).str.strip()

    for col in ["Y7LBSC", "Y7LBPR"]:
        open_prod_df[col] = pd.to_numeric(open_prod_df[col], errors="coerce").fillna(0)

    # Aggregate Open Yarn Production to YarnType / YarnColor level
    prod_agg = (
        open_prod_df
        .groupby(["Y7YNID", "Y7YCLR"], as_index=False)
        .agg(
            LbsScheduled=("Y7LBSC", "sum"),
            LbsProduced=("Y7LBPR", "sum"),
            OpenOrderCount=("Y7ORD#", "count"),
        )
        .rename(columns={"Y7YNID": "YarnType", "Y7YCLR": "YarnColor"})
    )
    prod_agg["LbsRemaining"] = (prod_agg["LbsScheduled"] - prod_agg["LbsProduced"]).round(4)

    # Merge: keep all YarnAlts rows, bring in production where available
    df = yarn_alts_df.merge(prod_agg, on=["YarnType", "YarnColor"], how="left")

    df["PlanningGroup"] = df["PlanningGroup"].fillna("Unlisted")
    df["ColorGroup"]    = df["ColorGroup"].fillna("Unlisted")

    for col in ["LbsScheduled", "LbsProduced", "LbsRemaining", "OpenOrderCount"]:
        df[col] = df[col].fillna(0)
    df["OpenOrderCount"] = df["OpenOrderCount"].astype(int)

    # Column order: 5 standard header cols + production metrics
    base_cols = [c for c in ["PlanningGroup", "ColorGroup", "YarnType", "YarnColor", "Supplier"] if c in df.columns]
    metric_cols = ["LbsScheduled", "LbsProduced", "LbsRemaining", "OpenOrderCount"]
    output_df = df[base_cols + metric_cols]

    output_path = export_folder / "Yarn Production Prebuild SKU.csv"
    output_df.to_csv(output_path, index=False)

    print(f"Prebuild SKU rows: {len(output_df)}")
    print(f"Prebuild SKU export: {output_path}")


if __name__ == "__main__":
    main()
