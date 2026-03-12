"""
Yarn Cycle Planner prebuild converter (starter)
Loads Yarn Alts and Cycle Planner Yarn Demand inputs and produces a staged output.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd

from utils import load_config, ensure_export_folder


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

    yarn_alts_df = pd.read_excel(yarn_alts_path, sheet_name=yarn_alts_sheet)
    yarn_demand_df = pd.read_csv(yarn_demand_path)

    output = {
        "yarn_alts_rows": len(yarn_alts_df),
        "cycle_planner_yarn_demand_rows": len(yarn_demand_df),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    summary_df = pd.DataFrame([output])
    summary_df.to_csv(export_folder / "Yarn Cycle Planner Prebuild.csv", index=False)


if __name__ == "__main__":
    main()
