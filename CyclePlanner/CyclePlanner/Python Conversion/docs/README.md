# CyclePlanner Python Conversion

## Configuration

All paths and parameters are controlled by `config.json`. Edit this file to customize locations.

### Config Structure

```json
{
  "paths": {
    "export_folder": "\\\\tdg-sa-file\\Atmore\\IE\\Cycle Planner",
    "planning_groups_xlsx": "\\\\tdg-sa-file\\Atmore\\IE\\Cycle Planner\\Planning Groups.xlsx",
    "sales_forecast_xlsx": "\\\\tdg-sa-file\\Atmore\\IE\\Cycle Planner\\SalesForecast.xlsx",
    "yarn_alts_xlsx": "\\\\tdg-sa-file\\Atmore\\IE\\Cycle Planner\\YarnAlts.xlsx"
  },
  "excel_sheets": {
    "planning_groups_sheet": "Sheet1",
    "sales_forecast_sheet": "SalesForecast",
    "yarn_alts_sheet": "YarnAlts"
  },
  "database": {
    "server": "TDG-DLT-IBMSQL",
    "database": "CAMS"
  },
  "parameters": {
    "inv_roll_cutoff": 100
  }
}
```

### Configuration Fields

#### Paths
- **export_folder**: Directory where CSV output files will be saved
- **planning_groups_xlsx**: Full path to Planning Groups.xlsx file
- **sales_forecast_xlsx**: Full path to SalesForecast.xlsx file
- **yarn_alts_xlsx**: Full path to YarnAlts.xlsx file

#### Excel Sheets
- **planning_groups_sheet**: Name of the worksheet in Planning Groups.xlsx (default: "Planning_Groups")
- **sales_forecast_sheet**: Name of the worksheet in SalesForecast.xlsx (default: "Sheet1")
- **yarn_alts_sheet**: Name of the worksheet in YarnAlts.xlsx (default: "YarnAlts")

#### Database
- **server**: SQL Server instance name
- **database**: Database name

#### Parameters
- **inv_roll_cutoff**: Minimum feet threshold for inventory rolls (filters out rolls with fewer feet)

## Usage

### Run All Converters (Recommended)

Run the master script to execute all Phase 1 converters:

```bash
python UpdateCyclePlanner.py
```

This runs:
1. Inventory Converter
2. Product Specs Converter
3. Sales Forecast Converter

Output shows success/failure for each converter with timing information.

### Run Individual Converters

```bash
python inventory_converter.py
python product_specs_converter.py
python sales_forecast_converter.py
```

### Testing (Mock Data)

Test without database or Excel file dependencies:

```bash
python test_phase1_converters.py
```

## Troubleshooting

### "Worksheet named 'X' not found"

If you get this error, the sheet name in config.json doesn't match the actual Excel file.

**Quick fix:** Run this helper script to see all available sheet names:
```bash
python list_excel_sheets.py
```

This will show all sheets in your configured Excel files. Then update `config.json` with the correct sheet name under `excel_sheets`.

## Output

CSV files are exported with timestamps:
- Format: `inventory_YYYYMMDD_HHMMSS.csv`
- Location: As specified in `config.json` under `paths.export_folder`

## Requirements

### Python Packages

Required:

```bash
pip install pandas numpy pyodbc openpyxl
```

Optional (for building executable):

```bash
pip install pyinstaller
```

If you use conda:

```bash
conda create -n cycleplanner python=3.11 -y
conda activate cycleplanner
conda install pandas numpy openpyxl pyodbc -y
pip install pyinstaller
```

### System Dependencies

- ODBC Driver 17 for SQL Server (or higher)
- Network access to database server and file shares

### Quick install (pip)

```bash
pip install pandas numpy pyodbc openpyxl
```
