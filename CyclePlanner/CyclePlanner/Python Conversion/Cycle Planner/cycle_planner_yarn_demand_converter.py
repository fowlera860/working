"""
Cycle Planner Yarn Demand Converter
Builds time-phased yarn demand (in lbs) from CyclePlannerPrebuild, YarnXRef, and YarnAlts
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    load_config,
    export_with_fallback,
    ensure_export_folder
)

REQUIRED_ALTS_COLUMNS = [
    "BaseType",
    "BaseColor",
    "AltNum",
    "AltType",
    "AltColor",
    "AltSupplier"
]

TIME_PHASE_WEEKS = 20
RECOMMENDED_COLUMN = "Recommened"
POSITION_COLUMN = "Position"
YARN_WEEK_PREFIX = "YR W "
PROJECTED_PRODUCTION_FILE = "projected_production.csv"


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


def load_yarn_alts(config: dict) -> pd.DataFrame:
    """Load YarnAlts.xlsx from config."""
    yarn_alts_path = Path(config["paths"]["yarn_alts_xlsx"])
    yarn_alts_sheet = config["excel_sheets"]["yarn_alts_sheet"]

    if not yarn_alts_path.exists():
        print(f"Error: YarnAlts file not found at {yarn_alts_path}")
        return pd.DataFrame()

    df = pd.read_excel(yarn_alts_path, sheet_name=yarn_alts_sheet, dtype="string")
    return df


def validate_yarn_alts(df: pd.DataFrame) -> bool:
    """Validate YarnAlts columns."""
    missing = [col for col in REQUIRED_ALTS_COLUMNS if col not in df.columns]
    if missing:
        print(f"Error: YarnAlts missing columns: {missing}")
        print(f"Found columns: {df.columns.tolist()}")
        return False
    return True


def normalize_keys(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Normalize key columns to clean strings."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].map(clean_key_value).astype("string")
    return df


def build_time_phase_lbs(
    cycle_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    yarn_alts_df: pd.DataFrame,
    weeks: int = TIME_PHASE_WEEKS
) -> pd.DataFrame:
    """Build time-phased recommended lbs by base yarn."""
    required = ["Style", "Color", "Size", POSITION_COLUMN, RECOMMENDED_COLUMN]
    missing = [col for col in required if col not in cycle_df.columns]
    if missing:
        print(f"Warning: Missing columns for time phase: {missing}")
        return pd.DataFrame()

    key_cols = ["Style", "Color", "Size"]
    cycle_subset = cycle_df[key_cols + [POSITION_COLUMN, RECOMMENDED_COLUMN]].copy()

    xref_subset = yarnxref_df[[
        "Style",
        "Color",
        "Size",
        "YarnType",
        "YarnColor",
        "OzSY"
    ]].copy()

    merged = cycle_subset.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged[POSITION_COLUMN] = pd.to_numeric(merged[POSITION_COLUMN], errors="coerce").fillna(0)
    merged[RECOMMENDED_COLUMN] = pd.to_numeric(merged[RECOMMENDED_COLUMN], errors="coerce").fillna(0)
    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)

    merged["Week"] = merged[POSITION_COLUMN].apply(lambda value: max(1, int(value)) if value > 0 else 1)
    merged["Week"] = merged["Week"].clip(lower=1, upper=weeks)

    merged["RecLbs"] = merged[RECOMMENDED_COLUMN] * (12 / 9) * (merged["OzSY"] / 16)

    mapped = merged.merge(
        yarn_alts_df,
        left_on=["YarnType", "YarnColor"],
        right_on=["AltType", "AltColor"],
        how="left"
    )

    mapped["BaseType"] = mapped["BaseType"].fillna(mapped["YarnType"])
    mapped["BaseColor"] = mapped["BaseColor"].fillna(mapped["YarnColor"])

    summary = (
        mapped.groupby(["BaseType", "BaseColor", "Week"])["RecLbs"]
        .sum()
        .reset_index()
    )

    if summary.empty:
        return pd.DataFrame()

    summary["Week"] = summary["Week"].apply(lambda week: f"{YARN_WEEK_PREFIX}{week:02d}")
    pivoted = summary.pivot_table(
        index=["BaseType", "BaseColor"],
        columns="Week",
        values="RecLbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, weeks + 1)]
    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    pivoted = pivoted[["BaseType", "BaseColor"] + week_cols]
    return pivoted


def build_time_phase_lbs_from_projected(
    projected_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    yarn_alts_df: pd.DataFrame,
    weeks: int = TIME_PHASE_WEEKS
) -> pd.DataFrame:
    """Build time-phased yarn demand lbs from projected production orders."""
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

    xref_subset = yarnxref_df[[
        "Style",
        "Color",
        "Size",
        "YarnType",
        "YarnColor",
        "OzSY"
    ]].copy()

    merged = orders.merge(xref_subset, on=key_cols, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["OzSY"] = pd.to_numeric(merged["OzSY"], errors="coerce").fillna(0)
    merged["RecLbs"] = merged["OrderSize"] * (12 / 9) * (merged["OzSY"] / 16)

    mapped = merged.merge(
        yarn_alts_df,
        left_on=["YarnType", "YarnColor"],
        right_on=["AltType", "AltColor"],
        how="left"
    )

    mapped["BaseType"] = mapped["BaseType"].fillna(mapped["YarnType"])
    mapped["BaseColor"] = mapped["BaseColor"].fillna(mapped["YarnColor"])

    summary = (
        mapped.groupby(["BaseType", "BaseColor", "Week #"])["RecLbs"]
        .sum()
        .reset_index()
    )

    if summary.empty:
        return pd.DataFrame()

    summary["Week"] = summary["Week #"].apply(lambda week: f"{YARN_WEEK_PREFIX}{int(week):02d}")
    pivoted = summary.pivot_table(
        index=["BaseType", "BaseColor"],
        columns="Week",
        values="RecLbs",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, weeks + 1)]
    for col in week_cols:
        if col not in pivoted.columns:
            pivoted[col] = 0.0

    return pivoted[["BaseType", "BaseColor"] + week_cols]


def build_yarn_rollup(
    cycle_df: pd.DataFrame,
    yarnxref_df: pd.DataFrame,
    yarn_alts_df: pd.DataFrame,
    projected_production_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Build base/alt yarn list from CyclePlannerPrebuild and xref/alt data."""
    key_cols = ["Style", "Color", "Size"]

    cycle_df = normalize_keys(cycle_df, key_cols)
    yarnxref_df = normalize_keys(yarnxref_df, key_cols + ["YarnType", "YarnColor"])

    cycle_keys = cycle_df[key_cols].drop_duplicates()
    xref_filtered = yarnxref_df.merge(cycle_keys, on=key_cols, how="inner")

    yarn_alts_df = normalize_keys(
        yarn_alts_df,
        ["BaseType", "BaseColor", "AltType", "AltColor"]
    )

    if projected_production_df is not None and not projected_production_df.empty:
        time_phase = build_time_phase_lbs_from_projected(projected_production_df, yarnxref_df, yarn_alts_df)
    else:
        time_phase = build_time_phase_lbs(cycle_df, yarnxref_df, yarn_alts_df)
    if not time_phase.empty:
        week_cols = [col for col in time_phase.columns if col.startswith(YARN_WEEK_PREFIX)]
    else:
        week_cols = [f"{YARN_WEEK_PREFIX}{i:02d}" for i in range(1, TIME_PHASE_WEEKS + 1)]

    if xref_filtered.empty:
        base_rows = (
            yarn_alts_df[["BaseType", "BaseColor"]]
            .drop_duplicates()
            .assign(
                Base="Y",
                YarnType=lambda df: df["BaseType"],
                YarnColor=lambda df: df["BaseColor"],
                AltSupplier="",
                SkuCount=0
            )
        )

        alt_rows = (
            yarn_alts_df[["BaseType", "BaseColor", "AltType", "AltColor", "AltSupplier"]]
            .drop_duplicates()
            .rename(columns={"AltType": "YarnType", "AltColor": "YarnColor"})
            .assign(Base="N", SkuCount=0)
        )

        combined = pd.concat([base_rows, alt_rows], ignore_index=True)

        combined["BaseSortType"] = combined["BaseType"]
        combined["BaseSortColor"] = combined["BaseColor"]
        combined["BaseSortFlag"] = combined["Base"].map({"Y": 0, "N": 1})

        for col in week_cols:
            combined[col] = 0.0

        combined = combined.sort_values(
            by=["BaseSortType", "BaseSortColor", "BaseSortFlag", "YarnType", "YarnColor"],
            kind="mergesort"
        )

        return combined[["Base", "YarnType", "YarnColor", "AltSupplier", "SkuCount"] + week_cols].reset_index(drop=True)

    mapped = xref_filtered.merge(
        yarn_alts_df,
        left_on=["YarnType", "YarnColor"],
        right_on=["AltType", "AltColor"],
        how="left"
    )

    mapped["SkuKey"] = (
        mapped["Style"].fillna("").astype(str)
        + "|" + mapped["Color"].fillna("").astype(str)
        + "|" + mapped["Size"].fillna("").astype(str)
    )

    mapped["BaseType"] = mapped["BaseType"].fillna(mapped["YarnType"])
    mapped["BaseColor"] = mapped["BaseColor"].fillna(mapped["YarnColor"])

    mapped["IsAlt"] = (
        mapped["YarnType"].fillna("") != mapped["BaseType"].fillna("")
    ) | (
        mapped["YarnColor"].fillna("") != mapped["BaseColor"].fillna("")
    )

    sku_counts = (
        mapped.groupby(["YarnType", "YarnColor"])["SkuKey"]
        .nunique()
        .reset_index()
        .rename(columns={"SkuKey": "SkuCount"})
    )

    base_sku_counts = (
        mapped.groupby(["BaseType", "BaseColor"])["SkuKey"]
        .nunique()
        .reset_index()
        .rename(columns={"SkuKey": "SkuCount"})
    )

    base_rows = (
        yarn_alts_df[["BaseType", "BaseColor"]]
        .drop_duplicates()
        .assign(
            Base="Y",
            YarnType=lambda df: df["BaseType"],
            YarnColor=lambda df: df["BaseColor"],
            AltSupplier=""
        )
        .merge(base_sku_counts, on=["BaseType", "BaseColor"], how="left")
    )

    base_rows["SkuCount"] = base_rows["SkuCount"].fillna(0).astype(int)

    alt_rows = (
        yarn_alts_df[["BaseType", "BaseColor", "AltType", "AltColor", "AltSupplier"]]
        .drop_duplicates()
        .rename(columns={"AltType": "YarnType", "AltColor": "YarnColor"})
        .assign(Base="N")
        .merge(sku_counts, on=["YarnType", "YarnColor"], how="left")
    )

    alt_rows["SkuCount"] = alt_rows["SkuCount"].fillna(0).astype(int)

    extra_bases = (
        mapped[["BaseType", "BaseColor"]]
        .drop_duplicates()
        .assign(
            Base="Y",
            YarnType=lambda df: df["BaseType"],
            YarnColor=lambda df: df["BaseColor"],
            AltSupplier=""
        )
        .merge(base_sku_counts, on=["BaseType", "BaseColor"], how="left")
    )

    extra_bases["SkuCount"] = extra_bases["SkuCount"].fillna(0).astype(int)

    extra_alts = (
        mapped[mapped["IsAlt"]][["BaseType", "BaseColor", "YarnType", "YarnColor"]]
        .drop_duplicates()
        .assign(Base="N", AltSupplier="")
        .merge(sku_counts, on=["YarnType", "YarnColor"], how="left")
    )

    extra_alts["SkuCount"] = extra_alts["SkuCount"].fillna(0).astype(int)

    combined = pd.concat([base_rows, alt_rows, extra_bases, extra_alts], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Base", "YarnType", "YarnColor"])

    if not time_phase.empty:
        combined = combined.merge(time_phase, on=["BaseType", "BaseColor"], how="left")
    else:
        for col in week_cols:
            combined[col] = 0.0

    combined[week_cols] = combined[week_cols].fillna(0)
    combined.loc[combined["Base"] == "N", week_cols] = 0.0

    combined["BaseSortType"] = combined["BaseType"]
    combined["BaseSortColor"] = combined["BaseColor"]
    combined["BaseSortFlag"] = combined["Base"].map({"Y": 0, "N": 1})

    combined = combined.sort_values(
        by=["BaseSortType", "BaseSortColor", "BaseSortFlag", "YarnType", "YarnColor"],
        kind="mergesort"
    )

    result = combined[["Base", "YarnType", "YarnColor", "AltSupplier", "SkuCount"] + week_cols].reset_index(drop=True)
    return result


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

    yarn_alts_df = load_yarn_alts(config)
    if yarn_alts_df.empty or not validate_yarn_alts(yarn_alts_df):
        return

    projected_production_df = load_projected_production(export_folder)
    if projected_production_df.empty:
        print(f"Warning: {PROJECTED_PRODUCTION_FILE} not found or empty. Falling back to prebuild recommendations.")
    else:
        print(f"Loaded projected production rows: {len(projected_production_df)}")

    cycle_df = trim_text_columns(cycle_df)
    yarnxref_df = trim_text_columns(yarnxref_df)
    yarn_alts_df = trim_text_columns(yarn_alts_df)

    rollup_df = build_yarn_rollup(cycle_df, yarnxref_df, yarn_alts_df, projected_production_df)

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


if __name__ == "__main__":
    main()
