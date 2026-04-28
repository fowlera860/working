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
        order_date = pd.to_datetime(order_date).date()
        weeks_diff = (order_date - current_week_sunday).days // 7
        return max(1, min(weeks_diff + 1, weeks))
    except Exception:
        return 1


def load_lot_aggregate(export_folder: Path) -> pd.DataFrame:
    """Load the Yarn Lot Aggregate CSV (all lots, unfiltered)."""
    filepath = export_folder / "Yarn Lot Aggregate.csv"
    if not filepath.exists():
        print("  ⚠ Yarn Lot Aggregate.csv not found — inventory will default to 0")
        return pd.DataFrame(
            columns=["LotNumber", "YarnType", "YarnColor", "FIN_Lbs", "WIP_Lbs", "PendingBalance", "Adjustment", "Total"]
        )
    return pd.read_csv(filepath, dtype={"LotNumber": str, "YarnType": str, "YarnColor": str})


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

    yarn_alts_df["YarnType"] = yarn_alts_df["YarnType"].str.strip()
    yarn_alts_df["YarnColor"] = yarn_alts_df["YarnColor"].str.strip()
    yarn_demand_df["YarnType"] = yarn_demand_df["YarnType"].str.strip()
    yarn_demand_df["YarnColor"] = yarn_demand_df["YarnColor"].str.strip()

    # Load lot aggregate and derive per-YarnType/YarnColor inventory components
    lot_agg = load_lot_aggregate(export_folder)
    min_lot_lbs = float(config.get("parameters", {}).get("min_lot_lbs", 500))

    def agg_by_type_color(col: str, rename_to: str, min_lbs_col: str = None) -> pd.DataFrame:
        if lot_agg.empty or col not in lot_agg.columns:
            return pd.DataFrame(columns=["YarnType", "YarnColor", rename_to])
        src = lot_agg.copy()
        src[col] = pd.to_numeric(src[col], errors="coerce").fillna(0)
        if min_lbs_col and min_lbs_col in src.columns:
            src[min_lbs_col] = pd.to_numeric(src[min_lbs_col], errors="coerce").fillna(0)
            src = src[src[min_lbs_col] >= min_lot_lbs]
        return (
            src.groupby(["YarnType", "YarnColor"], as_index=False)[col]
            .sum()
            .rename(columns={col: rename_to})
        )

    fin_inv = agg_by_type_color("FIN_Lbs",   "FIN Inventory",       min_lbs_col="FIN_Lbs")
    wip_inv = agg_by_type_color("WIP_Lbs",   "WIP Inventory")

    # Build the set of valid lots to filter pending orders.
    # Include lots that have FIN_Lbs >= min_lot_lbs OR have a meaningful PendingBalance.
    if not lot_agg.empty and "FIN_Lbs" in lot_agg.columns:
        lot_agg["FIN_Lbs"] = pd.to_numeric(lot_agg["FIN_Lbs"], errors="coerce").fillna(0)
        valid_fin_lots = lot_agg.loc[lot_agg["FIN_Lbs"] >= min_lot_lbs, "LotNumber"].astype(str).str.strip()
        if "PendingBalance" in lot_agg.columns:
            lot_agg["PendingBalance"] = pd.to_numeric(lot_agg["PendingBalance"], errors="coerce").fillna(0)
            valid_pending_lots = lot_agg.loc[lot_agg["PendingBalance"] > 0, "LotNumber"].astype(str).str.strip()
        else:
            valid_pending_lots = pd.Series(dtype=str)
        valid_lots = set(valid_fin_lots) | set(valid_pending_lots)
    else:
        valid_lots = set()

    # Compute SkuCount from YarnXRef — distinct Style/Color/Size per YarnType/YarnColor
    _yarnxref_csv_str = paths.get("yarnxref_csv", "")
    yarnxref_csv_path = Path(_yarnxref_csv_str) if _yarnxref_csv_str else None
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

    # Build output: demand is the base so yarns with demand but no YarnAlts entry are retained.
    # Yarns missing from YarnAlts get "Unlisted" for PlanningGroup and ColorGroup.
    df = yarn_alts_df.merge(demand_subset, on=["YarnType", "YarnColor"], how="right")
    df["PlanningGroup"] = df["PlanningGroup"].fillna("Unlisted")
    df["ColorGroup"] = df["ColorGroup"].fillna("Unlisted")

    df = df.merge(fin_inv,  on=["YarnType", "YarnColor"], how="left")
    df = df.merge(wip_inv,  on=["YarnType", "YarnColor"], how="left")
    df = df.merge(sku_counts, on=["YarnType", "YarnColor"], how="left")

    # Load and time-phase pending yarn orders by YarnType/YarnColor/Week
    po_week_cols = [f"PO W {i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    pending_orders_path = export_folder / "Pending Yarn Orders.csv"
    if pending_orders_path.exists():
        pending_df = pd.read_csv(pending_orders_path, dtype={"Y8TYPE": str, "Y8YCLR": str, "Y8LOT#": str})
        pending_df["Y8TYPE"] = pending_df["Y8TYPE"].str.strip()
        pending_df["Y8YCLR"] = pending_df["Y8YCLR"].str.strip()
        # Filter to only lots included in the aggregate (above min_lot_lbs threshold)
        if valid_lots and "Y8LOT#" in pending_df.columns:
            pending_df["Y8LOT#"] = pending_df["Y8LOT#"].astype(str).str.strip()
            before_po = len(pending_df)
            pending_df = pending_df[pending_df["Y8LOT#"].isin(valid_lots)]
            print(f"  Pending order rows filtered by valid lots: {before_po} → {len(pending_df)}")
        pending_df["OrderBalance"] = pd.to_numeric(pending_df["OrderBalance"], errors="coerce").fillna(0)
        pending_df["Week"] = pending_df["OrderDate"].apply(date_to_week)
        pending_df["WeekCol"] = pending_df["Week"].apply(lambda w: f"PO W {w:02d}")
        # --- diagnostic: show pending order week assignments for a specific yarn ---
        _debug_type, _debug_color = "7081", "5273"
        _debug_rows = pending_df[(pending_df["Y8TYPE"] == _debug_type) & (pending_df["Y8YCLR"] == _debug_color)]
        if not _debug_rows.empty:
            print(f"\n  [DEBUG] Pending orders for {_debug_type}/{_debug_color}:")
            print(_debug_rows[["Y8LOT#", "OrderDate", "OrderBalance", "Week", "WeekCol"]].to_string(index=False))
            print(f"  [DEBUG] Total PO balance: {_debug_rows['OrderBalance'].sum()}")
        # --- end diagnostic ---
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
        df = df.merge(pending_pivot, on=["YarnType", "YarnColor"], how="left")
    else:
        print("  ⚠ Pending Yarn Orders.csv not found — PO weeks will default to 0")

    for col in po_week_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)

    df["FIN Inventory"]        = df["FIN Inventory"].fillna(0)
    df["WIP Inventory"]        = df["WIP Inventory"].fillna(0)
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
        c for c in ["PlanningGroup", "ColorGroup", "YarnType", "YarnColor", "Supplier", "SkuCount"]
        if c in df.columns
    ]
    output_df = df[base_cols + ["FIN Inventory", "WIP Inventory", "Inventory", "Pending Orders", "Total Demand"] + po_week_cols + week_result_cols]

    output_path = export_folder / "Yarn Cycle Planner Prebuild.csv"
    output_df.to_csv(output_path, index=False)

    print(f"Prebuild rows: {len(output_df)}")
    print(f"Prebuild export: {output_path}")


if __name__ == "__main__":
    main()
