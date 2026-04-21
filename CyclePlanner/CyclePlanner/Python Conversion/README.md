# CyclePlanner Python Conversion

Complete Python conversion of the CyclePlanner Power Query workbook with SQL database integration.

## 📁 Project Structure

```
.
├── UpdateCyclePlanner.py           # Master script - runs all converters
├── config.json                      # Configuration (paths, database, parameters)
├── utils.py                         # Shared utility functions
│
├── Phase 1 - Foundation Converters
│   ├── inventory_converter.py
│   ├── product_specs_converter.py
│   └── sales_forecast_converter.py
│
├── Phase 2 - Mill Orders Converters
│   ├── mill_order_production_assignment_converter.py
│   ├── mill_order_roll_assignment_converter.py
│   ├── unassigned_mill_orders_converter.py
│   └── mill_orders_converter.py    # Combines all three
│
├── Phase 3 - Production & Time-Phased Converters
│   ├── production_orders_converter.py
│   ├── time_phase_production_orders_converter.py
│   └── time_phase_shipments_converter.py
│
├── Phase 4 - Master Consolidation
│   └── cycle_planner_prebuild_converter.py
│
├── docs/                            # 📚 Documentation
│   ├── README.md                    # Detailed project documentation
│   ├── QUICKSTART.md                # Quick setup guide
│   ├── PROJECT_STATUS.md            # Current status and completion details
│   ├── CONVERSION_PLAN.md           # Original conversion plan
│   ├── PHASE1_IMPLEMENTATION.md     # Phase 1 details
│   ├── PHASE2_IMPLEMENTATION.md     # Phase 2 details
│   ├── PHASE3_IMPLEMENTATION.md     # Phase 3 details
│   └── PHASE4_IMPLEMENTATION.md     # Phase 4 details
│
├── tests/                           # 🧪 Test files
│   ├── test_phase1_converters.py
│   ├── test_phase2_converters.py
│   ├── test_phase3_converters.py
│   └── test_phase4_converter.py
│
├── tools/                           # 🔧 Utility scripts
│   ├── list_excel_sheets.py         # List sheets in Excel files
│   ├── diagnose_imports.py          # Diagnose import issues
│   └── fix_encoding.py              # Fix file encoding problems
│
└── test_output/                     # Test output files
```

## 🚀 Quick Start

## 📦 Package Requirements

This project requires Python 3.10+ and the following packages:

- `pandas`
- `numpy`
- `pyodbc`
- `openpyxl`

Optional (only if building an exe):

- `pyinstaller`

### Install with pip
```bash
pip install pandas numpy pyodbc openpyxl
```

Optional build package:
```bash
pip install pyinstaller
```

### Install with conda
```bash
conda create -n cycleplanner python=3.11 -y
conda activate cycleplanner
conda install pandas numpy openpyxl pyodbc -y
pip install pyinstaller
```

System dependency:

- ODBC Driver 17+ for SQL Server must be installed on the machine.

### Run All Converters
```bash
python UpdateCyclePlanner.py
```

### Run Individual Converter
```bash
python inventory_converter.py
python mill_orders_converter.py
python cycle_planner_prebuild_converter.py
```

### Run Tests
```bash
python tests/test_phase1_converters.py
python tests/test_phase2_converters.py
python tests/test_phase3_converters.py
python tests/test_phase4_converter.py
```

## 📊 Output Files

All outputs are exported to the folder specified in `config.json`:

- `inventory.csv`
- `product_specs.csv`
- `sales_forecast.csv`
- `mill_orders.csv`
- `production_orders.csv`
- `time_phase_production_orders.csv`
- `time_phase_shipments.csv`
- **`cycle_planner_prebuild.csv`** ← Master output
- `projected_production.csv`
- `cycle_planner_yarn_demand.csv`

## ⚙️ Configuration

Edit `config.json` to customize:
- Export folder paths
- Excel file locations
- Database connection
- Parameters (e.g., inventory cutoff)

## 📖 Documentation

See [docs/README.md](docs/README.md) for comprehensive documentation including:
- Detailed converter descriptions
- Architecture patterns
- Database schema information
- Troubleshooting guide

## ✅ Status

**Base CyclePlanner conversion complete** (existing 8 converters operational)

- ✅ Phase 1: Foundation (3 converters)
- ✅ Phase 2: Mill Orders (4 converters)
- ✅ Phase 3: Time-Phased (3 converters)
- ✅ Phase 4: Master Consolidation (1 converter)

**Next Phase: Yarn Cycle Planner extension**

1) **Inputs**
	- Add YarnAlts.xlsx (single table) with columns:
	  - PlanningGroup, ColorGroup, YarnType, YarnColor, Supplier
	- Extend `yarnxref` converter to include `YarnColor`.

2) **Normalization Rules**
	- For each SKU (Style, Color, Size) in the report, ensure a matching `yarnxref` element exists.
	- If `YarnType`/`YarnColor` matches an `AltType`/`AltColor`, map to `BaseType`/`BaseColor`.
	- Otherwise use the values from `yarnxref`.

3) **New Output**
   - Generate a new report: `cycle_planner_yarn_demand.csv`.
   - Include grouped base type/color plus alts with:
     - SKU count
     - Time-phased demand (in lbs) based on Position and Recommended
