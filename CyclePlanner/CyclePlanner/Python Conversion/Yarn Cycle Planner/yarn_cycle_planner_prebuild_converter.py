"""
Yarn Cycle Planner prebuild converter.
Merges Yarn Alts, Yarn Demand, FIN inventory, and WIP inventory
into a time-phased planning output.
"""

from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

from utils import load_config, ensure_export_folder

TIME_PHASE_WEEKS = 20


def date_to_week(order_date, weeks: int = TIME_PHASE_WEEKS) -> int:
    """Convert an order date to a week number relative to the current week (Sunday-anchored)."""
    try:
        today = datetime.now().date()
        current_week_sunday = today - timedelta(days=today.weekday() + 1)
        if isinstance(order_date, str):
            order_date = datetime.strptime(order_date, "%Y-%m-%d").date()
        weeks_diff = (order_date - current_week_sunday).days // 7
        return max(1, min(weeks_diff + 1, weeks))
    except Exception:
        return 1


def load_inventory(export_folder: Path, filename: str, type_col: str, color_col: str) -> pd.DataFrame:
    """Load an inventory CSV and aggregate Y1NWGT by type + color."""
    filepath = export_folder / filename
    if not filepath.exists():
        print(f"  ⚠ {filename} not found — inventory will default to 0")
        return pd.DataFrame(columns=["YarnType", "YarnColor", "Y1NWGT"])

    df = pd.read_csv(filepath, dtype={type_col: str, color_col: str})
    df[type_col] = df[type_col].str.strip()
    df[color_col] = df[color_col].str.strip()
    df["Y1NWGT"] = pd.to_numeric(df["Y1NWGT"], errors="coerce").fillna(0)

    agg = df.groupby([type_col, color_col], as_index=False)["Y1NWGT"].sum()
    return agg.rename(columns={type_col: "YarnType", color_col: "YarnColor"})


def main() -> None:
    config = load_config()
    paths = config["paths"]

    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    yarn_alts_path = Path(paths["yarn_alts_xlsx"])
    yarn_demand_path = Path(paths["cycle_planner_yarn_demand_csv"])

    if not yarn_alts_path.exists():
        raise FileNotFoundError(f"Yarn Alts file not found: {yarn_alts_path}")
    if not yarn_demand_path.exists():
        raise FileNotFoundError(f"Cycle Planner Yarn Demand file not found: {yarn_demand_path}")

    yarn_alts_sheet = config.get("excel_sheets", {}).get("yarn_alts_sheet", "YarnAlts")

    yarn_alts_df = pd.read_excel(
        yarn_alts_path, sheet_name=yarn_alts_sheet, dtype=str
    )
    yarn_demand_df = pd.read_csv(
        yarn_demand_path, dtype=str
    )

    print(f"  YarnAlts columns: {list(yarn_alts_df.columns)}")
    print(f"  Yarn Demand columns: {list(yarn_demand_df.columns)}")

    yarn_alts_df["AltType"] = yarn_alts_df["AltType"].str.strip()
    yarn_alts_df["AltColor"] = yarn_alts_df["AltColor"].str.strip()
    yarn_demand_df["YarnType"] = yarn_demand_df["YarnType"].str.strip()
    yarn_demand_df["YarnColor"] = yarn_demand_df["YarnColor"].str.strip()

    # Load and aggregate inventory from exported CSVs
    fin_inv = load_inventory(export_folder, "FIN Yarn Inventory.csv", "Y1TYPE", "Y1YCLR")
    fin_inv = fin_inv.rename(columns={"Y1NWGT": "FIN Inventory"})

    wip_inv = load_inventory(export_folder, "WIP Yarn Inventory.csv", "Y1YNID", "Y1YCLR")
    wip_inv = wip_inv.rename(columns={"Y1NWGT": "WIP Inventory"})

    # Compute SkuCount from YarnXRef — distinct Style/Color/Size per YarnType/YarnColor
    yarnxref_csv_path = Path(paths.get("yarnxref_csv", ""))
    if yarnxref_csv_path and yarnxref_csv_path.exists():
        xref_df = pd.read_csv(yarnxref_csv_path, dtype={"Style": str, "Color": str, "Size": str, "YarnType": str, "YarnColor": str})
        for col in ["Style", "Color", "Size", "YarnType", "YarnColor"]:
            if col in xref_df.columns:
                xref_df[col] = xref_df[col].str.strip()
        xref_df["SkuKey"] = xref_df["Style"].fillna("") + "|" + xref_df["Color"].fillna("") + "|" + xref_df["Size"].fillna("")
        sku_counts = (
            xref_df.groupby(["YarnType", "YarnColor"])["SkuKey"]
            .nunique()
            .reset_index()
            .rename(columns={"SkuKey": "SkuCount"})
        )
    else:
        print("  ⚠ yarnxref.csv not found — SkuCount will default to 0")
        sku_counts = pd.DataFrame(columns=["YarnType", "YarnColor", "SkuCount"])

    # Pull only the week demand columns from yarn_demand_df
    week_demand_cols = [f"YR W {i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    present_week_cols = [c for c in week_demand_cols if c in yarn_demand_df.columns]

    # Demand file contains only YarnType, YarnColor, and week columns.
    raw_demand = yarn_demand_df[["YarnType", "YarnColor"] + present_week_cols].copy()
    for col in present_week_cols:
        raw_demand[col] = pd.to_numeric(raw_demand[col], errors="coerce").fillna(0)
    demand_subset = raw_demand.groupby(["YarnType", "YarnColor"], as_index=False).agg(
        {c: "sum" for c in present_week_cols}
    )

    # Build output: YarnAlts is the base, join demand on AltType/AltColor.
    # Demand is expressed at the yarn level — each alt row has its own demand entry.
    df = yarn_alts_df.merge(
        demand_subset, left_on=["AltType", "AltColor"], right_on=["YarnType", "YarnColor"], how="left"
    ).drop(columns=["YarnType", "YarnColor"])

    df = df.merge(fin_inv, left_on=["AltType", "AltColor"], right_on=["YarnType", "YarnColor"], how="left").drop(columns=["YarnType", "YarnColor"])
    df = df.merge(wip_inv, left_on=["AltType", "AltColor"], right_on=["YarnType", "YarnColor"], how="left").drop(columns=["YarnType", "YarnColor"])
    df = df.merge(sku_counts, left_on=["AltType", "AltColor"], right_on=["YarnType", "YarnColor"], how="left").drop(columns=["YarnType", "YarnColor"])

    # Load and time-phase pending yarn orders by YarnType/YarnColor/Week
    po_week_cols = [f"PO W {i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    pending_orders_path = export_folder / "Pending Yarn Orders.csv"
    if pending_orders_path.exists():
        pending_df = pd.read_csv(pending_orders_path, dtype={"Y8TYPE": str, "Y8YCLR": str})
        pending_df["Y8TYPE"] = pending_df["Y8TYPE"].str.strip()
        pending_df["Y8YCLR"] = pending_df["Y8YCLR"].str.strip()
        pending_df["OrderBalance"] = pd.to_numeric(pending_df["OrderBalance"], errors="coerce").fillna(0)
        pending_df["Week"] = pending_df["OrderDate"].apply(date_to_week)
        pending_df["WeekCol"] = pending_df["Week"].apply(lambda w: f"PO W {w:02d}")
        pending_pivot = (
            pending_df.groupby(["Y8TYPE", "Y8YCLR", "WeekCol"], as_index=False)["OrderBalance"]
            .sum()
            .pivot_table(index=["Y8TYPE", "Y8YCLR"], columns="WeekCol", values="OrderBalance", aggfunc="sum", fill_value=0)
            .reset_index()
            .rename(columns={"Y8TYPE": "YarnType", "Y8YCLR": "YarnColor"})
        )
        for col in po_week_cols:
            if col not in pending_pivot.columns:
                pending_pivot[col] = 0.0
        pending_pivot = pending_pivot[["YarnType", "YarnColor"] + po_week_cols]
        df = df.merge(pending_pivot, left_on=["AltType", "AltColor"], right_on=["YarnType", "YarnColor"], how="left").drop(columns=["YarnType", "YarnColor"])
    else:
        print("  ⚠ Pending Yarn Orders.csv not found — PO weeks will default to 0")

    for col in po_week_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)

    df["FIN Inventory"] = df["FIN Inventory"].fillna(0)
    df["WIP Inventory"] = df["WIP Inventory"].fillna(0)
    df["Inventory"] = df["FIN Inventory"] + df["WIP Inventory"]
    df["Pending Orders"] = df[po_week_cols].sum(axis=1)
    df["Total Demand"] = df[week_demand_cols].sum(axis=1)
    df["SkuCount"] = df["SkuCount"].fillna(0).astype(int)

    # Ensure all week demand columns are numeric
    for col in week_demand_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0.0

    # Calculate rolling time-phased balance (inventory + time-phased PO arrivals - demand)
    week_result_cols = []
    for i in range(1, TIME_PHASE_WEEKS + 1):
        result_col = f"Week {i:02d}"
        demand_col = f"YR W {i:02d}"
        po_col = f"PO W {i:02d}"
        week_result_cols.append(result_col)
        if i == 1:
            df[result_col] = (df["Inventory"] + df[po_col] - df[demand_col]).round(4)
        else:
            df[result_col] = (df[f"Week {i-1:02d}"] + df[po_col] - df[demand_col]).round(4)

    base_cols = [
        c for c in ["BaseType", "BaseColor", "AltNum", "AltType", "AltColor", "AltSupplier", "SkuCount"]
        if c in df.columns
    ]
    output_df = df[base_cols + ["FIN Inventory", "WIP Inventory", "Inventory", "Pending Orders", "Total Demand"] + po_week_cols + week_result_cols]

    output_path = export_folder / "Yarn Cycle Planner Prebuild.csv"
    output_df.to_csv(output_path, index=False)

    print(f"Prebuild rows: {len(output_df)}")
    print(f"Prebuild export: {output_path}")


if __name__ == "__main__":
    main()
