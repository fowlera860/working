# Quick Start Guide - Phase 1 Converters

## Overview

Phase 1 implements 2 foundation converters:
1. **Product Specs** - Extracts product specifications from database
2. **Sales Forecast** - Loads and processes sales forecast from Excel

Both are fully tested and ready to use.

## File Structure

```
Python Conversion/
├── config.json                      # Configuration (edit paths/sheet names here)
├── utils.py                         # Shared utilities for all converters
├── product_specs_converter.py       # Phase 1: Product specifications
├── sales_forecast_converter.py      # Phase 1: Sales forecast
├── test_phase1_converters.py        # Test with mock data
├── list_excel_sheets.py             # Helper to check Excel sheet names
├── PHASE1_IMPLEMENTATION.md         # Phase 1 details
└── test_output/                     # Test results
    ├── product_specs_test_*.csv
    └── sales_forecast_test_*.csv
```

## Setup

### 1. Verify Configuration

Check that `config.json` has correct paths:

```bash
python list_excel_sheets.py
```

This will show you available sheet names in your Excel files.

If you see sheet name errors, update `config.json`:

```json
{
  "excel_sheets": {
    "planning_groups_sheet": "YOUR_SHEET_NAME",
    "sales_forecast_sheet": "YOUR_SHEET_NAME"
  }
}
```

### 2. Test with Mock Data

Run the test to verify everything works:

```bash
python test_phase1_converters.py
```

Expected output:
```
✓ Phase 1 workflow test complete!
Product specs test output: test_output/product_specs_test_*.csv
Sales forecast test output: test_output/sales_forecast_test_*.csv
```

## Usage

### Run All Converters (Recommended)

The easiest way to run all Phase 1 converters:

```bash
python UpdateCyclePlanner.py
```

This runs all converters in sequence and provides a summary:
- ✓ Inventory
- ✓ Product Specifications
- ✓ Sales Forecast

### Run Individual Converters

**Product Specs (requires database connection):**
```bash
python product_specs_converter.py
```

**Sales Forecast (reads Excel only):**
```bash
python sales_forecast_converter.py
```

**Inventory (requires database connection):**
```bash
python inventory_converter.py
```

### Run All Phase 1 Manually

If you prefer to run them sequentially yourself:

```bash
python product_specs_converter.py && python sales_forecast_converter.py && python inventory_converter.py
```

## Output

Files are saved to `config.json` `paths.export_folder`:

- `product_specs.csv` - 13 columns: PlanningGroup, ColorGroup, Style, Color, Size, Back, StyleName, ColorName, RollSize, FaceWt, MachineNum, MachineDescription, EPN
- `sales_forecast.csv` - 18 columns: Style, Color, Size, Back, FC W 01-12, PlanGroup, ColorGroup

If a file is locked (open in Excel), it falls back to `product_specs_YYYYMMDD_HHMMSS.csv`

## Troubleshooting

### "Worksheet named 'X' not found"
Run: `python list_excel_sheets.py` to see actual sheet names and update config.json

### "Error connecting to database"
- Verify SQL Server is accessible: `TDG-DLT-IBMSQL`
- Check ODBC Driver 17 is installed
- Verify Trusted_Connection is available (Windows authentication)

### "Planning Groups file not found"
- Check network path in config.json is accessible: `\\tdg-sa-file\Atmore\IE\Cycle Planner`
- Verify Planning Groups.xlsx exists at that location

### "No data returned from database"
- Verify Planning_Groups has entries
- Check database permissions for CAMS database
- Verify filter criteria are correct (check planning group values)

## Next Steps

Once Phase 1 is working:

1. **Phase 2 (MillOrders)** - Combine 3 mill order queries
2. **Phase 3 (ProductionOrders)** - Production order details
3. **Phase 4 (TimePhase)** - Pivot to weekly formats
4. **Phase 5 (CyclePlannerPrebuild)** - Master consolidation

See [CONVERSION_PLAN.md](CONVERSION_PLAN.md) for full details.

## Key Features

✓ Config-driven - edit paths without changing code
✓ Mock testing - verify logic without database
✓ Error handling - helpful error messages
✓ File locking protection - fallback to timestamped names
✓ Shared utilities - reusable code patterns
✓ Extensible - easy to add new converters

## Support

For detailed implementation information, see:
- [PHASE1_IMPLEMENTATION.md](PHASE1_IMPLEMENTATION.md) - Phase 1 specifics
- [CONVERSION_PLAN.md](CONVERSION_PLAN.md) - Full conversion roadmap
- [README.md](README.md) - General setup
