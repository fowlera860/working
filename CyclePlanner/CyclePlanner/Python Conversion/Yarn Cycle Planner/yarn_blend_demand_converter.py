"""
Yarn Blend Demand converter for Yarn Cycle Planner.

Reads the tufting demand CSV and Yarn Blend XRef CSV (from yarn_blend_xref_converter)
to calculate additional demand on component yarns driven by finished yarn demand.

Logic:
  For each finished yarn → component yarn relationship in the xref at Pct %,
  the weekly demand of the finished yarn is multiplied by Pct/100 and attributed
  to the component yarn.  If multiple finished yarns blend into the same component,
  the contributions are summed.

  The finished yarn's own demand is NOT changed — only the component receives the
  addition.

Example:
  Yarn B (finished) has 800 lbs demand in Week 01.
  Xref: FinType=B, CompType=A, Pct=50
  → Component A receives +400 lbs in Week 01 (on top of its own tufting demand).

Output: Yarn Blend Demand.csv — the additional blend-derived demand per component
  yarn by week.  The prebuild converter adds this to the tufting demand at merge
  time.

  YarnType | YarnColor | YR W 01 | YR W 02 | … | YR W 20
"""

from pathlib import Path
from datetime import datetime

import pandas as pd

from utils import load_config, ensure_export_folder

TIME_PHASE_WEEKS = 20
WEEK_COLS = [f"YR W {i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]


def main() -> None:
    config = load_config()
    paths = config["paths"]
    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    demand_path = Path(paths["cycle_planner_yarn_demand_csv"])
    if not demand_path.exists():
        raise FileNotFoundError(f"Cycle Planner Yarn Demand file not found: {demand_path}")

    xref_path = export_folder / "Yarn Blend XRef.csv"
    if not xref_path.exists():
        raise FileNotFoundError(
            f"Yarn Blend XRef.csv not found: {xref_path}\n"
            "Run yarn_blend_xref_converter first."
        )

    # --- Load tufting demand ---
    demand_df = pd.read_csv(demand_path, dtype=str)
    demand_df["YarnType"] = demand_df["YarnType"].str.strip()
    demand_df["YarnColor"] = demand_df["YarnColor"].str.strip()

    present_week_cols = [c for c in WEEK_COLS if c in demand_df.columns]
    for col in present_week_cols:
        demand_df[col] = pd.to_numeric(demand_df[col], errors="coerce").fillna(0)

    # Aggregate finished yarn demand by YarnType/YarnColor (sum across any duplicate rows)
    fin_demand = (
        demand_df[["YarnType", "YarnColor"] + present_week_cols]
        .groupby(["YarnType", "YarnColor"], as_index=False)
        .agg({c: "sum" for c in present_week_cols})
    )

    # --- Load blend xref ---
    xref_df = pd.read_csv(
        xref_path,
        dtype={"FinType": str, "FinColor": str, "CompType": str, "CompColor": str},
    )
    for col in ["FinType", "FinColor", "CompType", "CompColor"]:
        xref_df[col] = xref_df[col].str.strip()
    xref_df["Pct"] = pd.to_numeric(xref_df["Pct"], errors="coerce").fillna(0)

    empty_output = pd.DataFrame(columns=["YarnType", "YarnColor"] + WEEK_COLS)
    fixed_output_path = export_folder / "Yarn Blend Demand.csv"

    if xref_df.empty:
        print("  ⚠ No blend cross-reference entries found — no blend demand generated")
        empty_output.to_csv(fixed_output_path, index=False)
        return

    # --- Join xref to finished yarn demand ---
    merged = xref_df.merge(
        fin_demand,
        left_on=["FinType", "FinColor"],
        right_on=["YarnType", "YarnColor"],
        how="inner",
    ).drop(columns=["YarnType", "YarnColor"])

    if merged.empty:
        print("  ⚠ No finished yarn demand found matching blend xref — no blend demand generated")
        empty_output.to_csv(fixed_output_path, index=False)
        return

    # --- Apply percentage factor to each week column ---
    for col in present_week_cols:
        merged[col] = (merged[col] * merged["Pct"] / 100.0).round(4)

    # --- Rename to component yarn identity and aggregate ---
    blend_df = (
        merged.rename(columns={"CompType": "YarnType", "CompColor": "YarnColor"})
        [["YarnType", "YarnColor"] + present_week_cols]
        .groupby(["YarnType", "YarnColor"], as_index=False)
        .agg({c: "sum" for c in present_week_cols})
    )

    # Ensure all 20 week columns are present (fill missing with 0)
    for col in WEEK_COLS:
        if col not in blend_df.columns:
            blend_df[col] = 0.0

    blend_df = blend_df[["YarnType", "YarnColor"] + WEEK_COLS]

    # --- Diagnostics ---
    total_blend_lbs = blend_df[WEEK_COLS].sum().sum()
    print(f"  Blend relationships matched: {len(merged)}")
    print(f"  Component yarns receiving blend demand: {len(blend_df)}")
    print(f"  Total blend demand added (all weeks): {total_blend_lbs:,.1f} lbs")

    if not blend_df.empty:
        print("\n  Top component yarns by blend demand:")
        blend_df["_total"] = blend_df[WEEK_COLS].sum(axis=1)
        top = blend_df.nlargest(10, "_total")[["YarnType", "YarnColor", "_total"]]
        top = top.rename(columns={"_total": "TotalBlendLbs"})
        print(top.to_string(index=False))
        blend_df = blend_df.drop(columns=["_total"])

    # --- Export ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"Yarn Blend Demand_{timestamp}.csv"

    try:
        blend_df.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        blend_df.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"\nYarn Blend Demand export: {output_path}")


if __name__ == "__main__":
    main()
