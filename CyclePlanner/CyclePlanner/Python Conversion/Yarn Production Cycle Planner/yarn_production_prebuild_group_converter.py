"""
Yarn Production Cycle Planner Prebuild - Group Level converter.

Aggregates the SKU-level prebuild up to PlanningGroup / ColorGroup,
then merges in Yarn Order Recommendations by those same two keys.
Output columns start with the same first 2 as the SKU prebuild:
  PlanningGroup | ColorGroup
followed by group-level aggregated metrics and order recommendation weeks.
"""

from pathlib import Path

import pandas as pd

from utils import load_config, ensure_export_folder


def main() -> None:
    config = load_config()
    paths = config["paths"]

    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    sku_prebuild_path    = export_folder / "Yarn Production Prebuild SKU.csv"
    order_rec_path       = export_folder / "Yarn Order Recommendations.csv"

    if not sku_prebuild_path.exists():
        raise FileNotFoundError(
            f"Yarn Production Prebuild SKU.csv not found: {sku_prebuild_path}\n"
            "Run the SKU prebuild converter first."
        )
    if not order_rec_path.exists():
        raise FileNotFoundError(
            f"Yarn Order Recommendations.csv not found: {order_rec_path}\n"
            "Run the yarn order recommendation converter first."
        )

    sku_df = pd.read_csv(sku_prebuild_path, dtype={"PlanningGroup": str, "ColorGroup": str})
    rec_df = pd.read_csv(order_rec_path,    dtype={"PlanningGroup": str, "ColorGroup": str})

    for col in ["PlanningGroup", "ColorGroup"]:
        sku_df[col] = sku_df[col].astype(str).str.strip()
        rec_df[col] = rec_df[col].astype(str).str.strip()

    # Aggregate SKU metrics to group level
    metric_cols = ["LbsScheduled", "LbsProduced", "LbsRemaining", "OpenOrderCount"]
    for col in metric_cols:
        if col in sku_df.columns:
            sku_df[col] = pd.to_numeric(sku_df[col], errors="coerce").fillna(0)

    present_metrics = [c for c in metric_cols if c in sku_df.columns]
    group_agg = (
        sku_df
        .groupby(["PlanningGroup", "ColorGroup"], as_index=False)[present_metrics]
        .sum()
    )
    group_agg["OpenOrderCount"] = group_agg["OpenOrderCount"].round(0).astype(int)

    # Pivot Yarn Order Recommendations: one row per PlanningGroup/ColorGroup,
    # one column per week — all weeks 1–TIME_PHASE_WEEKS are always present.
    TIME_PHASE_WEEKS = 20
    all_rec_week_cols = [f"Rec W {w:02d}" for w in range(1, TIME_PHASE_WEEKS + 1)]

    if "Week" in rec_df.columns and "Recommended Order" in rec_df.columns:
        rec_df["Week"] = pd.to_numeric(rec_df["Week"], errors="coerce")
        rec_df["WeekCol"] = rec_df["Week"].apply(lambda w: f"Rec W {int(w):02d}" if pd.notna(w) else None)
        rec_df = rec_df.dropna(subset=["WeekCol"])
        rec_df["Recommended Order"] = pd.to_numeric(rec_df["Recommended Order"], errors="coerce").fillna(0)

        rec_pivot = (
            rec_df
            .pivot_table(
                index=["PlanningGroup", "ColorGroup"],
                columns="WeekCol",
                values="Recommended Order",
                aggfunc="sum",
                fill_value=0,
            )
            .reset_index()
        )
        rec_pivot.columns.name = None

        # Ensure every week column exists, even weeks with no data
        for col in all_rec_week_cols:
            if col not in rec_pivot.columns:
                rec_pivot[col] = 0

        rec_week_cols = all_rec_week_cols
    else:
        rec_pivot    = pd.DataFrame(columns=["PlanningGroup", "ColorGroup"])
        rec_week_cols = all_rec_week_cols

    df = group_agg.merge(rec_pivot, on=["PlanningGroup", "ColorGroup"], how="left")

    for col in rec_week_cols:
        df[col] = df[col].fillna(0)

    # Column order: 2 standard header cols + production metrics + rec week cols
    output_cols = ["PlanningGroup", "ColorGroup"] + present_metrics + rec_week_cols
    output_df = df[output_cols]

    output_path = export_folder / "Yarn Production Prebuild Group.csv"
    output_df.to_csv(output_path, index=False)

    print(f"Prebuild Group rows: {len(output_df)}")
    print(f"Prebuild Group export: {output_path}")


if __name__ == "__main__":
    main()
