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

    xref = yarnxref_df[["Style", "Color", "Size", "YarnID", "YarnType", "YarnColor"]].copy()
    for col in ["Style", "Color", "Size"]:
        xref[col] = _clean_key(xref[col])
        df[col] = _clean_key(df[col])
    xref = xref.drop_duplicates(subset=["Style", "Color", "Size", "YarnID", "YarnType"])

    expanded = df.merge(xref, on=["Style", "Color", "Size"], how="inner")
    return expanded


def build_real_demand(production_orders_df: pd.DataFrame, yarnxref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand real production orders by yarn type/color.
    Returns Order #, Date, YarnType, YarnColor, Feet.
    """
    required = {"Style", "Color", "Size", "ProdNum", "PromiseDate", "OrderQty"}
    missing = required - set(production_orders_df.columns)
    if missing:
        print(f"Warning: production_orders missing columns: {missing}")
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet"])

    df = production_orders_df[["Style", "Color", "Size", "ProdNum", "PromiseDate", "OrderQty"]].copy()
    df["OrderQty"] = pd.to_numeric(df["OrderQty"], errors="coerce").fillna(0)
    df["ProdNum"] = df["ProdNum"].astype(str).str.strip()

    expanded = _expand_with_yarn(df, yarnxref_df)
    expanded = expanded.rename(columns={
        "ProdNum": "Order #",
        "PromiseDate": "Date",
        "OrderQty": "Feet"
    })
    return expanded[["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet"]]


def build_projected_demand(projected_production_df: pd.DataFrame, yarnxref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand projected production rows by yarn type/color.
    Returns Order # = "Projected", Date = Sunday of arrival week, YarnType, YarnColor, Feet.
    """
    required = {"Style", "Color", "Size", "Week #", "OrderSize"}
    missing = required - set(projected_production_df.columns)
    if missing:
        print(f"Warning: projected_production missing columns: {missing}")
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet"])

    df = projected_production_df[["Style", "Color", "Size", "Week #", "OrderSize"]].copy()
    df["Week #"] = pd.to_numeric(df["Week #"], errors="coerce").fillna(1).astype(int)
    df["OrderSize"] = pd.to_numeric(df["OrderSize"], errors="coerce").fillna(0)

    expanded = _expand_with_yarn(df, yarnxref_df)
    expanded["Order #"] = "Projected"
    expanded["Date"] = expanded["Week #"].apply(week_number_to_date)
    expanded = expanded.rename(columns={"OrderSize": "Feet"})

    return expanded[["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet"]]


def build_tufting_demand(
    production_orders_df: pd.DataFrame,
    projected_production_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame
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
        return pd.DataFrame(columns=["Order #", "Date", "Style", "Color", "Size", "YarnType", "YarnColor", "Feet"])

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["Feet"] > 0].reset_index(drop=True)
    return combined


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

    if production_orders_df.empty and projected_production_df.empty:
        print("Error: No data available for tufting demand export")
        return False

    if yarnxref_df.empty:
        print("Warning: YarnXRef is empty — output will have no YarnType/YarnColor")

    tufting_demand_df = build_tufting_demand(production_orders_df, projected_production_df, yarnxref_df)

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


if __name__ == "__main__":
    main()
