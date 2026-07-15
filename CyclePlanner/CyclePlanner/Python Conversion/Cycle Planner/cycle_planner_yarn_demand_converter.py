"""
Cycle Planner Yarn Demand Converter
Builds time-phased yarn demand (in lbs) from CyclePlannerPrebuild, YarnXRef, and YarnAlts
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from utils import (
    load_config,
    export_with_fallback,
    ensure_export_folder
)

TIME_PHASE_WEEKS = 20
RECOMMENDED_COLUMN = "Recommened"
POSITION_COLUMN = "Position"
YARN_WEEK_PREFIX = "YR W "
PROJECTED_PRODUCTION_FILE = "projected_production.csv"
PRODUCTION_ORDERS_FILE = "production_orders.csv"
AVG_FORECAST_COLUMN = "Avg Forecast"


def clean_key_value(value):
    """Convert keys to clean strings: trim whitespace, remove .0 suffixes."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def trim_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim all text columns in the DataFrame."""
    if df.empty:
        return df
    text_cols = [
        col for col in df.columns
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object
    ]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
    return df


def load_cycleplanner_prebuild(export_folder: Path) -> pd.DataFrame:
    """Load CyclePlannerPrebuild output from exports."""
    path = export_folder / "cycle_planner_prebuild.csv"
    if not path.exists():
        print(f"Error: Missing CyclePlannerPrebuild at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def load_yarnxref(export_folder: Path) -> pd.DataFrame:
    """Load YarnXRef output from exports."""
    path = export_folder / "yarnxref.csv"
    if not path.exists():
        print(f"Error: Missing YarnXRef at {path}")
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string"}
    df = pd.read_csv(path, dtype=dtype_dict)
    return df


def load_projected_production(export_folder: Path) -> pd.DataFrame:
    """Load projected production output from exports."""
    path = export_folder / PROJECTED_PRODUCTION_FILE
    if not path.exists():
        return pd.DataFrame()

    dtype_dict = {"Style": "string", "Color": "string", "Size": "string", "Back": "string"}
    return pd.read_csv(path, dtype=dtype_dict)


def normalize_keys(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Normalize key columns to clean strings."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].map(clean_key_value).astype("string")
    return df


def build_time_phase_lbs(
    cycle_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    weeks: int = TIME_PHASE_WEEKS
) -> pd.DataFrame:
    """Build time-phased lbs per yarn type/color."""
    required = ["Style", "Color", "Size", POSITION_COLUMN, RECOMMENDED_COLUMN]
    missing = [col for col in required if col not in cycle_df.columns]
    if missing:
        print(f"Warning: Missing columns for time phase: {missing}")
        return pd.DataFrame()

    key_cols = ["Style", "Color", "Size"]
    cycle_subset = cycle_df[key_cols + [POSITION_COLUMN, RECOMMENDED_COLUMN]].copy()
    xref_subset = yarnxref_df[["Style", "Color", "Size", "YarnType", "YarnColor", "OzSY"]].copy()

    merged = cycle_subset.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged[POSITION_COLUMN] = pd.to_numeric(merged[POSITION_COLUMN], errors="coerce").fillna(0)
    merged[RECOMMENDED_COLUMN] = pd.to_numeric(merged[RECOMMENDED_COLUMN], errors="coerce").fillna(0)
    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)

    merged["Week"] = merged[POSITION_COLUMN].apply(lambda value: max(1, int(value)) if value > 0 else 1)
    merged["Week"] = merged["Week"].clip(lower=1, upper=weeks)
    merged["RecLbs"] = merged[RECOMMENDED_COLUMN] * (12 / 9) * (merged["OzSY"] / 16)

    summary = (
        merged.groupby(["YarnType", "YarnColor", "Week"])["RecLbs"]
        .sum()
        .reset_index()
    )
    if summary.empty:
        return pd.DataFrame()

    summary["Week"] = summary["Week"].apply(lambda week: f"{YARN_WEEK_PREFIX}{week:02d}")
    pivoted = summary.pivot_table(
        index=["YarnType", "YarnColor"],
        columns="Week",
        values="RecLbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, weeks + 1)]
    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    return pivoted[["YarnType", "YarnColor"] + week_cols]


def build_time_phase_lbs_from_projected(
    projected_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    weeks: int = TIME_PHASE_WEEKS
) -> pd.DataFrame:
    """Build time-phased lbs per yarn type/color from projected production orders."""
    required = ["Style", "Color", "Size", "Week #", "OrderSize"]
    missing = [col for col in required if col not in projected_df.columns]
    if missing:
        print(f"Warning: Missing columns in projected production: {missing}")
        return pd.DataFrame()

    key_cols = ["Style", "Color", "Size"]
    orders = projected_df[key_cols + ["Week #", "OrderSize"]].copy()
    orders["Week #"] = pd.to_numeric(orders["Week #"], errors="coerce").fillna(1).astype(int)
    orders["Week #"] = orders["Week #"].clip(lower=1, upper=weeks)
    orders["OrderSize"] = pd.to_numeric(orders["OrderSize"], errors="coerce").fillna(0)

    orders = (
        orders.groupby(key_cols + ["Week #"], as_index=False, dropna=False)["OrderSize"]
        .sum()
    )

    xref_subset = yarnxref_df[["Style", "Color", "Size", "YarnType", "YarnColor", "OzSY"]].copy()

    merged = orders.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)
    merged["RecLbs"] = merged["OrderSize"] * (12 / 9) * (merged["OzSY"] / 16)

    summary = (
        merged.groupby(["YarnType", "YarnColor", "Week #"])["RecLbs"]
        .sum()
        .reset_index()
    )
    if summary.empty:
        return pd.DataFrame()

    summary["Week"] = summary["Week #"].apply(lambda week: f"{YARN_WEEK_PREFIX}{int(week):02d}")
    pivoted = summary.pivot_table(
        index=["YarnType", "YarnColor"],
        columns="Week",
        values="RecLbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, weeks + 1)]
    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    return pivoted[["YarnType", "YarnColor"] + week_cols]


def load_production_orders(export_folder: Path) -> pd.DataFrame:
    """Load real production orders from exports."""
    path = export_folder / PRODUCTION_ORDERS_FILE
    if not path.exists():
        print(f"  ⚠ {PRODUCTION_ORDERS_FILE} not found — real order demand will be 0")
        return pd.DataFrame()
    dtype_dict = {"Style": "string", "Color": "string", "Size": "string"}
    return pd.read_csv(path, dtype=dtype_dict)


def build_time_phase_lbs_from_real(
    production_orders_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    weeks: int = TIME_PHASE_WEEKS
) -> pd.DataFrame:
    """Build time-phased lbs per yarn type/color from real production orders."""
    required = ["Style", "Color", "Size", "PromiseDate", "OrderQty"]
    missing = [col for col in required if col not in production_orders_df.columns]
    if missing:
        print(f"Warning: Missing columns in production orders: {missing}")
        return pd.DataFrame()

    key_cols = ["Style", "Color", "Size"]
    orders = production_orders_df[key_cols + ["PromiseDate", "OrderQty"]].copy()
    orders["OrderQty"] = pd.to_numeric(orders["OrderQty"], errors="coerce").fillna(0)

    today = datetime.now().date()
    current_week_sunday = today - timedelta(days=today.weekday() + 1)

    def date_to_week_num(d):
        try:
            order_date = pd.to_datetime(d).date()
            diff = (order_date - current_week_sunday).days // 7
            return max(1, min(diff + 1, weeks))
        except Exception:
            return 1

    orders["Week #"] = orders["PromiseDate"].apply(date_to_week_num)

    xref_subset = yarnxref_df[["Style", "Color", "Size", "YarnType", "YarnColor", "OzSY"]].copy()
    merged = orders.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)
    merged["RecLbs"] = merged["OrderQty"] * (12 / 9) * (merged["OzSY"] / 16)

    summary = (
        merged.groupby(["YarnType", "YarnColor", "Week #"])["RecLbs"]
        .sum()
        .reset_index()
    )
    if summary.empty:
        return pd.DataFrame()

    summary["Week"] = summary["Week #"].apply(lambda w: f"{YARN_WEEK_PREFIX}{int(w):02d}")
    pivoted = summary.pivot_table(
        index=["YarnType", "YarnColor"],
        columns="Week",
        values="RecLbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, weeks + 1)]
    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    return pivoted[["YarnType", "YarnColor"] + week_cols]


def build_lbs_per_week(
    cycle_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build average weekly lbs per yarn type/color from Avg Forecast in the prebuild."""
    if AVG_FORECAST_COLUMN not in cycle_df.columns:
        print(f"Warning: '{AVG_FORECAST_COLUMN}' column not found in prebuild; LbsPerWeek will default to 0")
        return pd.DataFrame(columns=["YarnType", "YarnColor", "LbsPerWeek"])

    key_cols = ["Style", "Color", "Size"]
    cycle_subset = cycle_df[key_cols + [AVG_FORECAST_COLUMN]].copy()
    xref_subset = yarnxref_df[["Style", "Color", "Size", "YarnType", "YarnColor", "OzSY"]].copy()

    merged = cycle_subset.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame(columns=["YarnType", "YarnColor", "LbsPerWeek"])

    merged[AVG_FORECAST_COLUMN] = pd.to_numeric(merged[AVG_FORECAST_COLUMN], errors="coerce").fillna(0)
    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)
    merged["LbsPerWeek"] = merged[AVG_FORECAST_COLUMN] * (12 / 9) * (merged["OzSY"] / 16)

    return merged.groupby(["YarnType", "YarnColor"], as_index=False)["LbsPerWeek"].sum()


def build_yarn_rollup(
    cycle_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    projected_production_df: pd.DataFrame | None = None,
    production_orders_df: pd.DataFrame | None = None,
    waste_pct: float = 0.0
) -> pd.DataFrame:
    """Build time-phased yarn demand — only yarns with demand are returned."""
    key_cols = ["Style", "Color", "Size"]

    cycle_df = normalize_keys(cycle_df, key_cols)
    yarnxref_df = normalize_keys(yarnxref_df, key_cols + ["YarnType", "YarnColor"])

    if projected_production_df is not None and not projected_production_df.empty:
        time_phase = build_time_phase_lbs_from_projected(projected_production_df, yarnxref_df)
    else:
        time_phase = build_time_phase_lbs(cycle_df, yarnxref_df)

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]

    # Add real production order demand and sum with projected
    if production_orders_df is not None and not production_orders_df.empty:
        real_demand = build_time_phase_lbs_from_real(production_orders_df, yarnxref_df)
        if not real_demand.empty:
            print(f"  Real order demand yarn rows: {len(real_demand)}")
            if time_phase.empty:
                time_phase = real_demand
            else:
                combined = pd.concat([time_phase, real_demand], ignore_index=True)
                time_phase = combined.groupby(["YarnType", "YarnColor"], as_index=False)[week_cols].sum()

    if time_phase.empty:
        return pd.DataFrame(columns=["YarnType", "YarnColor", "LbsPerWeek"] + week_cols)

    # Compute LbsPerWeek from Avg Forecast (always from cycle_df, regardless of projected mode)
    lbs_per_week = build_lbs_per_week(cycle_df, yarnxref_df)

    multiplier = 1.0 + (waste_pct / 100.0) if waste_pct else 1.0

    if waste_pct:
        for col in week_cols:
            if col in time_phase.columns:
                time_phase[col] = time_phase[col] * multiplier

    if not lbs_per_week.empty:
        time_phase = time_phase.merge(lbs_per_week, on=["YarnType", "YarnColor"], how="left")
    else:
        time_phase["LbsPerWeek"] = 0.0
    time_phase["LbsPerWeek"] = (time_phase["LbsPerWeek"].fillna(0.0) * multiplier).round(4)

    col_order = ["YarnType", "YarnColor", "LbsPerWeek"] + [c for c in week_cols if c in time_phase.columns]
    return time_phase[col_order].sort_values(by=["YarnType", "YarnColor"], kind="mergesort").reset_index(drop=True)


def build_yarn_demand_detail(rollup_df: pd.DataFrame) -> pd.DataFrame:
    """Melt the time-phase rollup into long/column format: one row per (YarnType, YarnColor, Week)."""
    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    present_week_cols = [c for c in week_cols if c in rollup_df.columns]

    melted = rollup_df.melt(
        id_vars=["YarnType", "YarnColor", "LbsPerWeek"],
        value_vars=present_week_cols,
        var_name="Week",
        value_name="Lbs"
    )
    melted["Week"] = melted["Week"].str.replace(YARN_WEEK_PREFIX, "", regex=False).astype(int)
    melted = melted[melted["Lbs"] > 0].reset_index(drop=True)
    return melted[["YarnType", "YarnColor", "LbsPerWeek", "Week", "Lbs"]].sort_values(
        ["YarnType", "YarnColor", "Week"], kind="mergesort"
    ).reset_index(drop=True)


def main():
    """Main execution"""
    config = load_config()
    export_folder = Path(config["paths"]["export_folder"])

    print("=" * 60)
    print("Cycle Planner Yarn Demand")
    print("=" * 60)

    cycle_df = load_cycleplanner_prebuild(export_folder)
    if cycle_df.empty:
        return

    yarnxref_df = load_yarnxref(export_folder)
    if yarnxref_df.empty:
        return

    projected_production_df = load_projected_production(export_folder)
    if projected_production_df.empty:
        print(f"Warning: {PROJECTED_PRODUCTION_FILE} not found or empty. Falling back to prebuild recommendations.")
    else:
        print(f"Loaded projected production rows: {len(projected_production_df)}")

    production_orders_df = load_production_orders(export_folder)
    if not production_orders_df.empty:
        print(f"Loaded real production order rows: {len(production_orders_df)}")

    cycle_df = trim_text_columns(cycle_df)
    yarnxref_df = trim_text_columns(yarnxref_df)

    waste_pct = float(config.get("parameters", {}).get("percent_demand_yarn_waste", 0))
    print(f"Yarn waste factor: {waste_pct}%")

    rollup_df = build_yarn_rollup(cycle_df, yarnxref_df, projected_production_df, production_orders_df, waste_pct=waste_pct)

    if rollup_df.empty:
        print("No yarns found after applying xref and alt mapping")
        return

    if not ensure_export_folder(export_folder):
        return

    fixed_output_path = export_folder / "cycle_planner_yarn_demand.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_output_path = export_folder / f"cycle_planner_yarn_demand_{timestamp}.csv"

    output_path, success = export_with_fallback(
        rollup_df,
        fixed_output_path,
        timestamped_output_path
    )

    if not success:
        return

    print(f"Exported to: {output_path}")
    print(f"Total rows: {len(rollup_df)}")
    print("\nFirst few rows:")
    print(rollup_df.head(10))

    # Also export column/detail format (one row per YarnType/YarnColor/Week)
    detail_df = build_yarn_demand_detail(rollup_df)
    fixed_detail_path = export_folder / "cycle_planner_yarn_demand_detail.csv"
    timestamped_detail_path = export_folder / f"cycle_planner_yarn_demand_detail_{timestamp}.csv"
    detail_path, detail_success = export_with_fallback(detail_df, fixed_detail_path, timestamped_detail_path)
    if detail_success:
        print(f"\nDetail export: {detail_path} ({len(detail_df)} rows)")


if __name__ == "__main__":
    main()
