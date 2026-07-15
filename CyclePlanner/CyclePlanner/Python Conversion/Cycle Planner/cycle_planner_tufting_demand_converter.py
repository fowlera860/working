"""
Cycle Planner Tufting Demand Converter
Produces a flat order-level view of every tufting run that feeds yarn demand,
expanded by yarn type and color via the YarnXRef.

Real orders: from production_orders.csv (one row per production order)
Projected orders: from projected_production.csv (one row per SKU/week projection)

Output columns:
  Order #    — production order number, or "Projected" for projected demand
  Date       — promise date for real orders; Sunday of the arrival week for projected
  Style      — carpet style
  Color      — carpet color
  Size       — carpet size
  YarnType   — yarn type from YarnXRef
  YarnColor  — yarn color from YarnXRef
  Feet       — linear feet ordered / projected
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from utils import (
    load_config,
    export_with_fallback,
    ensure_export_folder
)

PROJECTED_PRODUCTION_FILE = "projected_production.csv"
PRODUCTION_ORDERS_FILE = "production_orders.csv"
YARNXREF_FILE = "yarnxref.csv"
PRODUCT_SPECS_FILE = "product_specs.csv"
TIME_PHASE_WEEKS = 20
YARN_WEEK_PREFIX = "YR W "


def _current_week_sunday() -> "datetime.date":
    """Return the Sunday that starts the current planning week."""
    today = datetime.now().date()
    # weekday(): Monday=0 … Sunday=6; adding 1 rolls Sunday (6) to 7 → offset 7 → same day
    return today - timedelta(days=today.weekday() + 1)


def week_number_to_date(week_num: int) -> "datetime.date":
    """Convert a planning week number (1-based) to the Sunday of that week."""
    return _current_week_sunday() + timedelta(weeks=week_num - 1)


def load_production_orders(export_folder: Path) -> pd.DataFrame:
    """Load real production orders from exports."""
    path = export_folder / PRODUCTION_ORDERS_FILE
    if not path.exists():
        print(f"Warning: {PRODUCTION_ORDERS_FILE} not found at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string", "Back": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def load_projected_production(export_folder: Path) -> pd.DataFrame:
    """Load projected production orders from exports."""
    path = export_folder / PROJECTED_PRODUCTION_FILE
    if not path.exists():
        print(f"Warning: {PROJECTED_PRODUCTION_FILE} not found at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string", "Back": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def load_yarnxref(export_folder: Path) -> pd.DataFrame:
    """Load YarnXRef from exports."""
    path = export_folder / YARNXREF_FILE
    if not path.exists():
        print(f"Warning: {YARNXREF_FILE} not found at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string",
                  "YarnID": "string", "YarnType": "string", "YarnColor": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def load_product_specs(export_folder: Path) -> pd.DataFrame:
    """Load product specs from exports."""
    path = export_folder / PRODUCT_SPECS_FILE
    if not path.exists():
        print(f"Warning: {PRODUCT_SPECS_FILE} not found at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def _clean_key(series: pd.Series) -> pd.Series:
    """Normalize a key column: strip whitespace, drop trailing .0."""
    s = series.astype(str).str.strip()
    s = s.where(~s.str.endswith(".0"), s.str[:-2])
    return s.astype("string")


def _expand_with_yarn(df: pd.DataFrame, yarnxref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join df (must have Style, Color, Size) with yarnxref to produce one row
    per (order-row × yarn type/color combination).
    Returns the expanded DataFrame with YarnType and YarnColor added.
    If yarnxref is empty, returns df with empty YarnType/YarnColor columns.
    """
    if yarnxref_df.empty:
        df["YarnType"] = pd.NA
        df["YarnColor"] = pd.NA
        return df

    xref_cols = ["Style", "Color", "Size", "YarnID", "YarnType", "YarnColor"]
    if "OzSY" in yarnxref_df.columns:
        xref_cols.append("OzSY")
    xref = yarnxref_df[xref_cols].copy()
    for col in ["Style", "Color", "Size"]:
        xref[col] = _clean_key(xref[col])
        df[col] = _clean_key(df[col])
    xref = xref.drop_duplicates(subset=["Style", "Color", "Size", "YarnID", "YarnType"])

    expanded = df.merge(xref, on=["Style", "Color", "Size"], how="inner")
    return expanded


def build_real_demand(production_orders_df: pd.DataFrame, yarnxref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand real production orders by yarn type/color.
    Returns Order #, Date, Style, Color, Size, YarnType, YarnColor, Feet, Lbs.
    """
    required = {"Style", "Color", "Size", "ProdNum", "PromiseDate", "OrderQty"}
    missing = required - set(production_orders_df.columns)
    if missing:
        print(f"Warning: production_orders missing columns: {missing}")
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs"])

    df = production_orders_df[["Style", "Color", "Size", "ProdNum", "PromiseDate", "OrderQty"]].copy()
    df["OrderQty"] = pd.to_numeric(df["OrderQty"], errors="coerce").fillna(0)
    df["ProdNum"] = df["ProdNum"].astype(str).str.strip()

    expanded = _expand_with_yarn(df, yarnxref_df)
    expanded = expanded.rename(columns={
        "ProdNum": "Order #",
        "PromiseDate": "Date",
        "OrderQty": "Feet"
    })
    if "OzSY" in expanded.columns:
        expanded["OzSY"] = pd.to_numeric(expanded["OzSY"], errors="coerce").fillna(0)
        expanded["Lbs"] = (expanded["Feet"] * (12 / 9) * (expanded["OzSY"] / 16)).round(4)
        expanded = expanded.drop(columns=["OzSY"])
    else:
        expanded["Lbs"] = 0.0
    return expanded[["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs"]]


def build_projected_demand(projected_production_df: pd.DataFrame, yarnxref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand projected production rows by yarn type/color.
    Returns Order # = "Projected", Date = Sunday of arrival week, YarnType, YarnColor, Feet, Lbs.
    """
    required = {"Style", "Color", "Size", "Week #", "OrderSize"}
    missing = required - set(projected_production_df.columns)
    if missing:
        print(f"Warning: projected_production missing columns: {missing}")
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs"])

    df = projected_production_df[["Style", "Color", "Size", "Week #", "OrderSize"]].copy()
    df["Week #"] = pd.to_numeric(df["Week #"], errors="coerce").fillna(1).astype(int)
    df["OrderSize"] = pd.to_numeric(df["OrderSize"], errors="coerce").fillna(0)

    expanded = _expand_with_yarn(df, yarnxref_df)
    expanded["Order #"] = "Projected"
    expanded["Date"] = expanded["Week #"].apply(week_number_to_date)
    expanded = expanded.rename(columns={"OrderSize": "Feet"})
    if "OzSY" in expanded.columns:
        expanded["OzSY"] = pd.to_numeric(expanded["OzSY"], errors="coerce").fillna(0)
        expanded["Lbs"] = (expanded["Feet"] * (12 / 9) * (expanded["OzSY"] / 16)).round(4)
        expanded = expanded.drop(columns=["OzSY"])
    else:
        expanded["Lbs"] = 0.0

    return expanded[["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs"]]


def build_tufting_demand(
    production_orders_df: pd.DataFrame,
    projected_production_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    product_specs_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """Combine real and projected demand into a single flat table, expanded by yarn."""
    frames = []

    if not production_orders_df.empty:
        real = build_real_demand(production_orders_df, yarnxref_df)
        if not real.empty:
            frames.append(real)

    if not projected_production_df.empty:
        projected = build_projected_demand(projected_production_df, yarnxref_df)
        if not projected.empty:
            frames.append(projected)

    if not frames:
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs", "DyeType"])

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["Feet"] > 0].reset_index(drop=True)

    if product_specs_df is not None and not product_specs_df.empty and "DyeType" in product_specs_df.columns:
        dye_map = product_specs_df[["Style", "Color", "Size", "DyeType"]].copy()
        for col in ["Style", "Color", "Size"]:
            dye_map[col] = _clean_key(dye_map[col])
        dye_map = dye_map.drop_duplicates(subset=["Style", "Color", "Size"])
        combined = combined.merge(dye_map, on=["Style", "Color", "Size"], how="left")
    else:
        combined["DyeType"] = pd.NA

    return combined[["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet", "Lbs", "DyeType"]]


def build_tufting_demand_time_phase(tufting_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot tufting demand into time-phase format matching blend_demand: YarnType × YarnColor × week columns."""
    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    if tufting_df.empty:
        return pd.DataFrame(columns=["YarnType", "YarnColor"] + week_cols)

    df = tufting_df[["Date", "YarnType", "YarnColor", "Lbs"]].copy()
    df["Lbs"] = pd.to_numeric(df["Lbs"], errors="coerce").fillna(0)

    today = datetime.now().date()
    current_week_sunday = today - timedelta(days=today.weekday() + 1)

    def date_to_week_num(d):
        try:
            order_date = pd.to_datetime(d).date()
            diff = (order_date - current_week_sunday).days // 7
            return max(1, min(diff + 1, TIME_PHASE_WEEKS))
        except Exception:
            return 1

    df["WeekCol"] = df["Date"].apply(date_to_week_num).apply(lambda w: f"{YARN_WEEK_PREFIX}{int(w):02d}")

    pivoted = df.pivot_table(
        index=["YarnType", "YarnColor"],
        columns="WeekCol",
        values="Lbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    pivoted.columns.name = None

    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    return pivoted[["YarnType", "YarnColor"] + week_cols].sort_values(
        ["YarnType", "YarnColor"], kind="mergesort"
    ).reset_index(drop=True)


def main():
    """Main execution"""
    config = load_config()
    export_folder = Path(config["paths"]["export_folder"])

    print("=" * 60)
    print("Cycle Planner Tufting Demand")
    print("=" * 60)

    production_orders_df = load_production_orders(export_folder)
    projected_production_df = load_projected_production(export_folder)
    yarnxref_df = load_yarnxref(export_folder)
    product_specs_df = load_product_specs(export_folder)

    if production_orders_df.empty and projected_production_df.empty:
        print("Error: No data available for tufting demand export")
        return False

    if yarnxref_df.empty:
        print("Warning: YarnXRef is empty — output will have no YarnType/YarnColor")

    if product_specs_df.empty or "DyeType" not in product_specs_df.columns:
        print("Warning: product_specs missing or has no DyeType column — DyeType will be blank")

    tufting_demand_df = build_tufting_demand(production_orders_df, projected_production_df, yarnxref_df, product_specs_df)

    if tufting_demand_df.empty:
        print("No tufting demand rows found")
        return False

    if not ensure_export_folder(export_folder):
        return False

    fixed_output_path = export_folder / "tufting_demand.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"tufting_demand_{timestamp}.csv"

    output_path, success = export_with_fallback(
        tufting_demand_df,
        fixed_output_path,
        timestamped_output_path
    )

    if not success:
        return False

    unique_skus = tufting_demand_df[["Style", "Color", "Size"]].drop_duplicates().shape[0]

    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(tufting_demand_df)}")
    print(f"  Real orders:      {(tufting_demand_df['Order #'] != 'Projected').sum()}")
    print(f"  Projected orders: {(tufting_demand_df['Order #'] == 'Projected').sum()}")
    print(f"  Unique SKUs matched in YarnXRef: {unique_skus}")
    print("\nFirst few rows:")
    print(tufting_demand_df.head(10))

    # Also export time-phase format (YarnType × YarnColor × week columns, matching blend_demand)
    time_phase_df = build_tufting_demand_time_phase(tufting_demand_df)
    fixed_tp_path = export_folder / "tufting_demand_time_phase.csv"
    timestamped_tp_path = export_folder / f"tufting_demand_time_phase_{timestamp}.csv"
    tp_path, tp_success = export_with_fallback(time_phase_df, fixed_tp_path, timestamped_tp_path)
    if tp_success:
        print(f"\nTime-phase export: {tp_path} ({len(time_phase_df)} yarn type/color rows)")


if __name__ == "__main__":
    main()
