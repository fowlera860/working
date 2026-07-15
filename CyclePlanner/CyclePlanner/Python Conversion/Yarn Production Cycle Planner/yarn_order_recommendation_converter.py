"""
Yarn Order Recommendation converter for Yarn Production Cycle Planner.
Copies the Yarn Order Recommendations CSV from the Yarn Cycle Planner exports
into this planner's export folder.
"""

from pathlib import Path

import pandas as pd

from utils import load_config, ensure_export_folder


def main() -> None:
    config = load_config()
    paths = config["paths"]

    source_path = Path(paths["yarn_order_recommendation_csv"])
    if not source_path.exists():
        raise FileNotFoundError(
            f"Yarn Order Recommendations source not found: {source_path}\n"
            "Ensure the Yarn Cycle Planner has been run first."
        )

    df = pd.read_csv(source_path)

    export_folder = Path(paths["export_folder"])
    ensure_export_folder(export_folder)

    output_path = export_folder / "Yarn Order Recommendations.csv"
    df.to_csv(output_path, index=False)

    print(f"Yarn order recommendation rows: {len(df)}")
    print(f"Yarn order recommendation export: {output_path}")


if __name__ == "__main__":
    main()
