"""
Helper script to list all sheet names in an Excel file
Usage: python list_excel_sheets.py "path/to/file.xlsx"
"""

import sys
import pandas as pd
from pathlib import Path

def list_sheets(excel_path: str):
    """List all sheet names in an Excel file"""
    try:
        xl_file = pd.ExcelFile(excel_path)
        print(f"\nSheet names in: {excel_path}")
        print("=" * 60)
        for i, sheet in enumerate(xl_file.sheet_names, 1):
            print(f"{i}. {sheet}")
        print("=" * 60)
        print(f"Total: {len(xl_file.sheet_names)} sheets\n")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try to use config.json
        try:
            import json
            config_path = Path(__file__).parent / "config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print("\nChecking files from config.json:")
            print("\n" + "=" * 60)
            print("Planning Groups:")
            list_sheets(config['paths']['planning_groups_xlsx'])
            
            if 'sales_forecast_xlsx' in config['paths']:
                print("\n" + "=" * 60)
                print("Sales Forecast:")
                list_sheets(config['paths']['sales_forecast_xlsx'])
        except Exception as e:
            print(f"Usage: python {sys.argv[0]} <excel_file_path>")
            print(f"\nOr place this script in the same folder as config.json")
            print(f"Error: {e}")
    else:
        list_sheets(sys.argv[1])
