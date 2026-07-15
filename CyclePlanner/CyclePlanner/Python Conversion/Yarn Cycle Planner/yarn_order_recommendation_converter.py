"""
Yarn Order Recommendation converter for Yarn Cycle Planner.

Groups the Yarn Cycle Planner Prebuild by PlanningGroup + ColorGroup, sums
the time-phased balance columns across all YarnType/YarnColor rows in each
group, then applies the order trigger logic for each starting week from
new_order_trigger_week through the last viable week:

  For each starting week w:
    - Window: weeks w … TIME_PHASE_WEEKS (summed values).
    - If ANY value in that window is >= 0  →  Recommended Order = 0
    - If ALL values are negative           →  Recommended Order = summed value
                                               at week (w + new_order_demand_weeks - 1)

Output: Yarn Order Recommendations.csv
  PlanningGroup | ColorGroup | Week | Recommended Order
"""

from pathlib import Path

import pandas as pd

from utils import load_config, ensure_export_folder

TIME_PHASE_WEEKS = 20


def main() -> None:
    config = load_config()
    paths  = config["paths"]
    params = config.get("parameters", {})

    trigger_week = int(params.get("new_order_trigger_week", 5))
    demand_weeks = int(params.get("new_order_demand_weeks",  4))

    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    prebuild_path = export_folder / "Yarn Cycle Planner Prebuild.csv"
    if not prebuild_path.exists():
        raise FileNotFoundError(
            f"Yarn Cycle Planner Prebuild.csv not found: {prebuild_path}\n"
            "Run the prebuild converter first."
        )

    df = pd.read_csv(prebuild_path, dtype={"PlanningGroup": str, "ColorGroup": str})

    for col in ["PlanningGroup", "ColorGroup"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        else:
            df[col] = "Unlisted"

    # Identify the time-phase week balance columns present in the file
    week_cols = [f"Week {i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]
    present_week_cols = [c for c in week_cols if c in df.columns]

    for col in present_week_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Sum timephase values across all YarnType/YarnColor rows within each group
    group_sums = (
        df.groupby(["PlanningGroup", "ColorGroup"], as_index=False)[present_week_cols]
        .sum()
    )

    # Last valid starting week: need demand_weeks weeks of room ahead
    last_start = TIME_PHASE_WEEKS - demand_weeks + 1

    # Precompute per-week metadata (column names) so the group loop stays clean
    week_configs = []
    for w in range(trigger_week, last_start + 1):
        trigger_col    = f"Week {w:02d}"
        max_demand_col = f"Week {w + demand_weeks - 1:02d}"
        if trigger_col not in present_week_cols or max_demand_col not in present_week_cols:
            continue
        window_cols = [c for c in present_week_cols if int(c.split()[1]) >= w]
        week_configs.append((w, max_demand_col, window_cols))

    # Outer loop is group so each group carries its own cumulative_production state
    rows = []
    for _, group_row in group_sums.iterrows():
        # Running total of projected production already scheduled for this group.
        # Each triggered order adds its production quantity here, shifting all
        # future week values upward before re-evaluating the next trigger window.
        cumulative_production = 0.0

        for w, max_demand_col, window_cols in week_configs:
            # Adjust window values by any previously projected production
            window_values = [group_row[c] + cumulative_production for c in window_cols]

            if any(v >= 0 for v in window_values):
                rec = 0.0
            else:
                max_idx = window_cols.index(max_demand_col)
                rec = window_values[max_idx]  # already adjusted
                # rec is negative (shortage); add its absolute value to future production
                cumulative_production += (-rec)

            rows.append({
                "PlanningGroup":     group_row["PlanningGroup"],
                "ColorGroup":        group_row["ColorGroup"],
                "Week":              w,
                "Recommended Order": rec,
            })

    output_df = pd.DataFrame(rows, columns=["PlanningGroup", "ColorGroup", "Week", "Recommended Order"])

    output_path = export_folder / "Yarn Order Recommendations.csv"
    output_df.to_csv(output_path, index=False)

    print(f"Order recommendation rows: {len(output_df)}")
    print(f"Export: {output_path}")


if __name__ == "__main__":
    main()
