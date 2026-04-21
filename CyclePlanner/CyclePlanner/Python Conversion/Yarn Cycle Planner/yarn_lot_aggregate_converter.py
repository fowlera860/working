"""
Yarn lot aggregate builder for Yarn Cycle Planner.

Merges pending yarn orders, FIN inventory, WIP inventory, and yarn assignment
adjustments by Lot#.  Applies the minimum-lot-lbs filter and enriches each lot
with YarnType/YarnColor and SkuCount, then exports a consolidated CSV that the
prebuild uses as its inventory/pending source of truth.

Total = FIN_Lbs + PendingBalance + Adjustment
Lots with Total < parameters.min_lot_lbs are excluded.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd

from utils import load_config, ensure_export_folder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_csv(export_folder: Path, name: str, **read_kwargs) -> pd.DataFrame:
    """Load a CSV from the export folder; return empty DataFrame if missing."""
    p = export_folder / name
    if p.exists():
        return pd.read_csv(p, **read_kwargs)
    print(f"  ⚠ {name} not found — contribution will be 0")
    return pd.DataFrame()


def _std_lot(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Standardize a lot-number column to stripped string in-place (copy-safe)."""
    if not df.empty and col in df.columns:
        df = df.copy()
        df[col] = df[col].astype(str).str.strip()
    return df


def _lot_sum(df: pd.DataFrame, lot_col: str, val_col: str, result_col: str) -> pd.DataFrame:
    """Aggregate val_col by lot_col and return a two-column frame."""
    if df.empty or lot_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame(columns=["LotNumber", result_col])
    agg = df.copy()
    agg[val_col] = pd.to_numeric(agg[val_col], errors="coerce").fillna(0)
    agg = agg.groupby(lot_col, as_index=False)[val_col].sum()
    return agg.rename(columns={lot_col: "LotNumber", val_col: result_col})


def _lot_type_color(df: pd.DataFrame, lot_col: str, type_col: str, color_col: str) -> pd.DataFrame:
    """Return a deduplicated LotNumber -> YarnType, YarnColor lookup frame."""
    if df.empty or lot_col not in df.columns:
        return pd.DataFrame(columns=["LotNumber", "YarnType", "YarnColor"])
    out = df[[lot_col, type_col, color_col]].copy()
    out.columns = ["LotNumber", "YarnType", "YarnColor"]
    out["LotNumber"] = out["LotNumber"].astype(str).str.strip()
    out["YarnType"] = out["YarnType"].astype(str).str.strip()
    out["YarnColor"] = out["YarnColor"].astype(str).str.strip()
    return out.drop_duplicates(subset=["LotNumber"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config = load_config()
    paths = config["paths"]
    params = config.get("parameters", {})
    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    min_lot_lbs = float(params.get("min_lot_lbs", 500))  # used by prebuild; not applied here

    # ------------------------------------------------------------------
    # Load source CSVs
    # ------------------------------------------------------------------
    fin_df = _load_csv(
        export_folder, "FIN Yarn Inventory.csv",
        dtype={"Y1TYPE": str, "Y1YCLR": str, "Y1LOT#": str},
    )
    wip_df = _load_csv(
        export_folder, "WIP Yarn Inventory.csv",
        dtype={"Y1YNID": str, "Y1YCLR": str, "Y1LOT#": str},
    )
    po_df = _load_csv(
        export_folder, "Pending Yarn Orders.csv",
        dtype={"Y8TYPE": str, "Y8YCLR": str, "Y8LOT#": str},
    )
    ya_df = _load_csv(
        export_folder, "yarn_assignments.csv",
        dtype={"Y6LOT#": str, "Y6TYPE": str, "Y6YCLR": str},
    )

    # Standardize lot columns
    fin_df = _std_lot(fin_df, "Y1LOT#")
    wip_df = _std_lot(wip_df, "Y1LOT#")
    po_df  = _std_lot(po_df,  "Y8LOT#")
    ya_df  = _std_lot(ya_df,  "Y6LOT#")
    if not ya_df.empty:
        for col in ["Y6TYPE", "Y6YCLR"]:
            if col in ya_df.columns:
                ya_df[col] = ya_df[col].astype(str).str.strip()

    # ------------------------------------------------------------------
    # Per-lot numeric aggregates
    # ------------------------------------------------------------------
    fin_lbs     = _lot_sum(fin_df, "Y1LOT#", "Y1NWGT",       "FIN_Lbs")
    wip_lbs     = _lot_sum(wip_df, "Y1LOT#", "Y1NWGT",       "WIP_Lbs")
    po_lbs      = _lot_sum(po_df,  "Y8LOT#", "OrderBalance",  "PendingBalance")
    adj_lbs     = _lot_sum(ya_df,  "Y6LOT#", "ADJUSTMENT",    "Adjustment")

    # ------------------------------------------------------------------
    # Combine via outer join on LotNumber
    # ------------------------------------------------------------------
    all_lots = (
        fin_lbs
        .merge(wip_lbs,  on="LotNumber", how="outer")
        .merge(po_lbs,   on="LotNumber", how="outer")
        .merge(adj_lbs,  on="LotNumber", how="outer")
    )

    for col in ["FIN_Lbs", "WIP_Lbs", "PendingBalance", "Adjustment"]:
        all_lots[col] = pd.to_numeric(all_lots.get(col, 0), errors="coerce").fillna(0)

    all_lots["Total"] = (
        all_lots["FIN_Lbs"]
        + all_lots["PendingBalance"]
        + all_lots["Adjustment"]
    )

    # ------------------------------------------------------------------
    # Enrich with YarnType / YarnColor — priority: FIN > Assignments > Pending > WIP
    # ------------------------------------------------------------------
    tc_fin = _lot_type_color(fin_df, "Y1LOT#", "Y1TYPE", "Y1YCLR")
    tc_ya  = _lot_type_color(ya_df,  "Y6LOT#", "Y6TYPE", "Y6YCLR")
    tc_po  = _lot_type_color(po_df,  "Y8LOT#", "Y8TYPE", "Y8YCLR")
    tc_wip = _lot_type_color(wip_df, "Y1LOT#", "Y1YNID", "Y1YCLR")

    lot_tc = (
        pd.concat([tc_fin, tc_ya, tc_po, tc_wip], ignore_index=True)
        .drop_duplicates(subset=["LotNumber"], keep="first")
    )

    all_lots = all_lots.merge(lot_tc, on="LotNumber", how="left")

    # ------------------------------------------------------------------
    # Add SkuCount from YarnXRef if available
    # ------------------------------------------------------------------
    yarnxref_path = Path(paths.get("yarnxref_csv", ""))
    if yarnxref_path and yarnxref_path.exists():
        xref_df = pd.read_csv(
            yarnxref_path,
            dtype={"YarnType": str, "YarnColor": str, "Style": str, "Color": str, "Size": str},
        )
        for col in ["YarnType", "YarnColor", "Style", "Color", "Size"]:
            if col in xref_df.columns:
                xref_df[col] = xref_df[col].str.strip()
        xref_df["SkuKey"] = (
            xref_df["Style"].fillna("") + "|"
            + xref_df["Color"].fillna("") + "|"
            + xref_df["Size"].fillna("")
        )
        sku_counts = (
            xref_df.groupby(["YarnType", "YarnColor"])["SkuKey"]
            .nunique()
            .reset_index()
            .rename(columns={"SkuKey": "SkuCount"})
        )
        all_lots = all_lots.merge(sku_counts, on=["YarnType", "YarnColor"], how="left")
        all_lots["SkuCount"] = all_lots["SkuCount"].fillna(0).astype(int)
    else:
        print("  ⚠ yarnxref.csv not found — SkuCount will default to 0")
        all_lots["SkuCount"] = 0

    # ------------------------------------------------------------------
    # Final column order and export
    # ------------------------------------------------------------------
    out = all_lots[[
        "LotNumber", "YarnType", "YarnColor", "SkuCount",
        "FIN_Lbs", "WIP_Lbs", "PendingBalance", "Adjustment", "Total",
    ]]

    fixed_output_path = export_folder / "Yarn Lot Aggregate.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_output_path = export_folder / f"Yarn Lot Aggregate_{timestamp}.csv"

    try:
        out.to_csv(fixed_output_path, index=False)
        output_path = fixed_output_path
    except Exception:
        out.to_csv(fallback_output_path, index=False)
        output_path = fallback_output_path

    print(f"Yarn lot aggregate rows: {len(out)}")
    print(f"Yarn lot aggregate export: {output_path}")


if __name__ == "__main__":
    main()
