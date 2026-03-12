# CyclePlanner Python Conversion - Project Status

**Last Updated:** February 18, 2026  
**Status:** ✅ Phase 1-4 Complete & Tested  
**All 8 Converters:** ✅ Running Successfully

---

## Executive Summary

The CyclePlanner Power Query workbook has been successfully converted to Python with SQL database integration. All core converters are operational and producing validated outputs. The system is modular, configuration-driven, and ready for production use plus the Yarn Cycle Planner extension.

**Completion:** 
- Phase 1 (Foundation): 3/3 converters ✅
- Phase 2 (Mill Orders): 4/4 converters ✅  
- Phase 3 (Production Orders & Time-Phased): 3/3 converters ✅
- Phase 4 (Master Consolidation): 1/1 converter ✅
- **Total: 8/8 converters complete**

---

## What's Working

### Master Orchestration Script

**File:** `UpdateCyclePlanner.py`

Runs all 8 converters in sequence with error handling and reporting:

```bash
python UpdateCyclePlanner.py
```

**Output:**
```
======================================================================
  CyclePlanner Update - Phase 1-4
======================================================================
Started: 2026-01-23 15:03:55

  ✓ SUCCESS: Inventory
  ✓ SUCCESS: Product Specifications
  ✓ SUCCESS: Sales Forecast
  ✓ SUCCESS: Mill Orders (Combined)
  ✓ SUCCESS: Production Orders
  ✓ SUCCESS: Time-Phase Production Orders
  ✓ SUCCESS: Time-Phase Shipments
  ✓ SUCCESS: Cycle Planner Prebuild

✓ All converters completed successfully!
Duration: 19.83 seconds
```

---

## Phase 1: Foundation Converters

### 1. Inventory Converter
**File:** `inventory_converter.py`  
**Source:** FIP010 table (active inventory)  
**Output:** `inventory.csv`  
**Columns:** Style, Color, Size, Back, FeetAvailable, PlanGroup, ColorGroup, WeeksOut  
**Filters:** 
- Active rolls (F1ACT=0)
- Quality approved (F1QLTY=1)
- Non-sales flag empty (F1SFLG='')
- Minimum feet (F1ALTF > inv_roll_cutoff, default 100)

**Key Feature:** Groups by Planning Groups, filters by inventory threshold

---

### 2. Product Specifications Converter
**File:** `product_specs_converter.py`  
**Source:** FIP020/FIP020B (styles), FIP712/FIP715 (roll specs), GIP030 (machines)  
**Output:** `product_specs.csv`  
**Columns:** 13 columns including Style, Color, Size, Back, StyleName, ColorName, RollSize, FaceWt, MachineNum, MachineDescription, EPN  
**Key Feature:** Multi-table join with Planning Groups filter

---

### 3. Sales Forecast Converter
**File:** `sales_forecast_converter.py`  
**Source:** SalesForecast.xlsx (Excel file)  
**Output:** `sales_forecast.csv`  
**Columns:** Style, Color, Size, Back, FC W 01-12 (forecast weeks), PlanGroup, ColorGroup  
**Key Feature:** Loads Excel, removes non-forecast columns, joins Planning Groups

---

## Phase 2: Mill Orders Converters

### Combined Mill Orders (4 Converters)

**Master File:** `mill_orders_converter.py`  
**Output:** `mill_orders.csv`

**Individual Converters:**
1. **Production Assignment** (`mill_order_production_assignment_converter.py`)
   - Source: PRP010 table
   - Calculates: RsvQty (reserved), PendingProd (pending production)
   
2. **Roll Assignment** (`mill_order_roll_assignment_converter.py`)
   - Source: FIP010 table (active rolls with orders)
   - Filters: F1ACT < 7, F1AORD <> 0
   
3. **Unassigned Orders** (`unassigned_mill_orders_converter.py`)
   - Source: OPP010 table (unassigned orders)
   - Filters: O1CNCD=0, O1OCJL=0, O1AQTY=0, O1AJUL=0

**Combined Output Columns:** 
Style, Color, Size, Back, Src (source type), OrdNum, OrdLine, Qty, UOM, PromDt, RsvQty, PendingProd, AsgQty, ProdOrder, LF, WeeksOut

**Key Feature:** Normalizes columns across 3 data sources, adds WeeksOut calculation

---

## Phase 3: Production Orders & Time-Phased Converters

### 1. Production Orders Converter
**File:** `production_orders_converter.py`  
**Source:** PPP010 table (production planning)  
**Output:** `production_orders.csv`  
**Columns:** Style, Color, Size, Back, ProdNum, OrderQty, ProdDate, PromiseDate, MachineNum, Seq, WeeksOut  
**Key Feature:** Filters latest sequence per product; converts Julian dates to standard dates; excludes completed orders

---

### 2. Time-Phase Production Orders Converter
**File:** `time_phase_production_orders_converter.py`  
**Source:** Production Orders data (pivoted)  
**Output:** `time_phase_production_orders.csv`  
**Columns:** Style, Color, Size, Back, PD W 01...PD W 13 (13 weeks of planned production)  
**Key Feature:** Pivots order quantities to weekly buckets; reuses production orders data

---

### 3. Time-Phase Shipments Converter
**File:** `time_phase_shipments_converter.py`  
**Source:** Mill Orders data (pivoted)  
**Output:** `time_phase_shipments.csv`  
**Columns:** Style, Color, Size, Back, SH W 01...SH W 13 (13 weeks of shipments)  
**Key Feature:** Pivots shipment quantities to weekly buckets; combines 3 order sources into time-phased view

---

## Architecture & Patterns

### Shared Utilities Library
**File:** `utils.py` (7 reusable functions)

1. **load_config()** - Reads config.json
2. **load_planning_groups()** - Loads Excel with error handling
3. **build_group_filter_cte()** - Creates SQL CTE from Planning Groups
4. **get_weeks_out()** - Calculates weeks from current Sunday to promise date
5. **pivot_to_weeks()** - Pivots data into week columns (1-13)
6. **export_with_fallback()** - Exports CSV with locked-file fallback
7. **ensure_export_folder()** - Creates export directory

### Configuration System
**File:** `config.json`

```json
{
  "paths": {
    "export_folder": "\\tdg-sa-file\Atmore\IE\Cycle Planner\exports",
    "planning_groups_xlsx": "\\tdg-sa-file\Atmore\IE\Cycle Planner\Planning Groups.xlsx",
    "sales_forecast_xlsx": "\\tdg-sa-file\Atmore\IE\Cycle Planner\SalesForecast.xlsx"
  },
  "excel_sheets": {
    "planning_groups_sheet": "Sheet1",
    "sales_forecast_sheet": "SalesForecast"
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

**How to Customize:**
- Update network paths in `paths` section
- Change Excel sheet names if they differ
- Adjust `inv_roll_cutoff` for inventory minimum threshold

### Module Reloading
**UpdateCyclePlanner.py** uses `importlib.reload()` to ensure latest converter code is executed in production runs.

---

## Data Flow Architecture

```
Excel Files                          Database (SQL Server)
├─ Planning Groups.xlsx    ────┐     TDG-DLT-IBMSQL / CAMS
└─ SalesForecast.xlsx      ────┤     ├─ FIP010, FIP020, FIP020B, FIP712, FIP715, GIP030
                               │     ├─ PRP010, OPP010, PPP010
Config (config.json)       ────┤     └─ data.* schema
                               ↓
                          ┌────────────────────────────┐
                          │  Shared Utilities (utils)  │
                          │  ├─ SQL CTE builder       │
                          │  ├─ Date calculations      │
                          │  ├─ Pivot logic            │
                          │  └─ Export handlers        │
                          └────────────────────────────┘
                               ↓
                    ┌──────────────────────────┐
                    │  Phase 1 Converters      │
                    ├─ Inventory              │
                    ├─ Product_Specs          │
                    └─ Sales_Forecast         │
                               ↓
                    ┌──────────────────────────┐
                    │  Phase 2 Converters      │
                    ├─ MillOrderPA            │
                    ├─ MillOrderRA            │
                    ├─ UnassignedOrders       │
                    └─ Combined MillOrders    │
                               ↓
                    ┌──────────────────────────┐
                    │  Phase 3 Converters      │
                    ├─ Production Orders      │
                    ├─ TimePhaseProductionOrd │
                    └─ TimePhaseShipments     │
                               ↓
                         CSV Exports
                    ├─ inventory.csv
                    ├─ product_specs.csv
                    ├─ sales_forecast.csv
                    ├─ mill_orders.csv
                    ├─ production_orders.csv
                    ├─ time_phase_production_orders.csv
                    ├─ time_phase_shipments.csv
                    └─ cycle_planner_prebuild.csv
```

---

## Testing

### Mock Data Tests
**Files:**
- `test_phase1_converters.py` - Phase 1 logic validation
- `test_phase2_converters.py` - Phase 2 logic validation
- `test_phase3_converters.py` - Phase 3 logic validation

**Run Tests:**
```bash
python test_phase1_converters.py
python test_phase2_converters.py
python test_phase3_converters.py
```

**Result:** All mock tests pass ✅

### Production Validation
Last successful run:
- **Date:** 2026-01-23 15:03:55
- **Duration:** 19.83 seconds
- **All 8 Converters:** ✅ SUCCESS
- **Total Rows Processed:** 188 production orders + 3 mill order sources + inventory + specs + forecast

---

## Known Patterns & Conventions

### Column Naming
- Planning Groups: `Style, Color, Size, Back, PlanGroup, ColorGroup`
- Dates: `PromDt` (mill orders), `PromiseDate` (production orders), Julian integers converted to dates
- Time-Phased: `PD W 01...PD W 13` (production), `SH W 01...SH W 13` (shipments)
- Quantities: `OrderQty, Qty, FtOrdered, RsvQty, PendingProd`

### Week Calculations
- Current week: Sunday (start of week)
- WeeksOut: 1-13 max, calculated from current Sunday to promise date
- Past/current week dates: WeeksOut = 1

### Julian Date Conversion
- Power Query: `PPJULN + 366` then cast to date
- Python: `datetime('1899-12-31') + timedelta(julian + 366)`

### Error Handling
- File existence checks before loading
- Graceful degradation for missing files (dev/test environments)
- CSV export with timestamped fallback if file locked
- Database connection errors caught with helpful messages

---

## File Structure

```
CyclePlanner/
├── CyclePlanner/
│   ├── Python Conversion/
│   │   ├── UpdateCyclePlanner.py          [Master orchestration]
│   │   ├── utils.py                       [Shared utilities]
│   │   ├── config.json                    [Configuration]
│   │   │
│   │   ├── Phase 1 - Foundation
│   │   ├─ inventory_converter.py
│   │   ├─ product_specs_converter.py
│   │   ├─ sales_forecast_converter.py
│   │   ├─ test_phase1_converters.py
│   │   │
│   │   ├── Phase 2 - Mill Orders
│   │   ├─ mill_order_production_assignment_converter.py
│   │   ├─ mill_order_roll_assignment_converter.py
│   │   ├─ unassigned_mill_orders_converter.py
│   │   ├─ mill_orders_converter.py
│   │   ├─ test_phase2_converters.py
│   │   │
│   │   ├── Phase 3 - Production Orders & Time-Phased
│   │   ├─ production_orders_converter.py
│   │   ├─ time_phase_production_orders_converter.py
│   │   ├─ time_phase_shipments_converter.py
│   │   ├─ test_phase3_converters.py
│   │   │
│   │   ├── Documentation
│   │   ├─ PROJECT_STATUS.md               [This file]
│   │   ├─ PHASE1_IMPLEMENTATION.md
│   │   ├─ PHASE2_IMPLEMENTATION.md
│   │   └─ PHASE3_IMPLEMENTATION.md
│   │
│   ├── [Original Power Query files]
│   └── exports/                           [CSV output folder]
```

---

## Quick Start

### Run Everything
```bash
cd "C:\path\to\CyclePlanner\CyclePlanner\Python Conversion"
python UpdateCyclePlanner.py
```

### Run Individual Converter
```bash
python inventory_converter.py
python mill_orders_converter.py
python production_orders_converter.py
```

### Run Tests
```bash
python test_phase1_converters.py
python test_phase2_converters.py
python test_phase3_converters.py
```

### Configure for Your Environment
Edit `config.json`:
- Update network share paths
- Adjust sheet names if needed
- Modify `inv_roll_cutoff` if desired

---

## Next Steps: Phase 5 (Yarn Demand Extension)

### Cycle Planner Yarn Demand
Build a yarn-focused demand report that uses YarnAlts.xlsx and the YarnXRef converter.

**Current Functionality:**
1. Added YarnAlts.xlsx input (single table)
2. Extended `yarnxref` to include `YarnColor`
3. Normalize to BaseType/BaseColor when AltType/AltColor matches
4. Creates `cycle_planner_yarn_demand.csv` with grouped base type/color plus alts

**Output Columns:**
- Base, YarnType, YarnColor, AltSupplier
- SKU count
- Time-phased demand (YR W 01...YR W 20) in lbs based on Position and Recommended

---

## Dependencies

### Python Packages
- pandas - Data manipulation & CSV I/O
- pyodbc - SQL Server database connectivity
- openpyxl - Excel file reading
- sqlalchemy (optional) - For SQLAlchemy connection string support

### System Requirements
- Python 3.7+
- ODBC Driver 17 for SQL Server (installed & configured)
- Network access to:
  - TDG-DLT-IBMSQL server (CAMS database)
  - \\tdg-sa-file\Atmore\IE\Cycle Planner (Excel files & exports)
- Windows authentication with database access

---

## Success Criteria ✅

- [x] Phase 1: 3/3 converters created and tested
- [x] Phase 2: 4/4 converters created and tested
- [x] Phase 3: 3/3 converters created and tested
- [x] Phase 4: 1/1 converter created and tested
- [x] Master script (UpdateCyclePlanner.py) orchestrates all 8
- [x] Configuration system with customizable paths
- [x] Shared utilities library for code reuse
- [x] CSV exports with fallback file handling
- [x] Mock data tests for all phases (all passing)
- [x] Database integration tested
- [x] Error handling & graceful degradation
- [x] Documentation complete

---

## Support & Troubleshooting

### Common Issues

**File Not Found Errors:**
- Check config.json paths are correct
- Verify network share is accessible
- Confirm Excel files exist at specified locations

**Database Connection Errors:**
- Verify ODBC Driver 17 is installed
- Check SQL Server connectivity
- Confirm Windows authentication works
- Test with SQL Server Management Studio

**Permission Errors on Export:**
- Ensure export folder exists and is writable
- Check file lock (file might be open in Excel)
- System will automatically fall back to timestamped filename

**Column Name Errors:**
- Verify Excel sheet names in config.json
- Check database table schemas match expected columns
- Review error message for actual vs. expected column names

---

## Notes for Next Session

1. **Phase 1-4 are production-ready** - All converters tested and working
2. **CSV exports are in:** `\\tdg-sa-file\Atmore\IE\Cycle Planner\exports\`
3. **Update script runs in ~20 seconds** for full pipeline
4. **Configuration is externalized** in config.json for easy customization
5. **Modular architecture** supports the Yarn extension as a separate phase
6. **Mock tests** available for validation before production runs

---

## Summary

The CyclePlanner Power Query workbook has been successfully converted to Python. The system is modular, well-documented, tested, and ready for daily use plus the Yarn Cycle Planner extension. All 8 converters are operational and producing validated CSV outputs.

**Status: ✅ Complete & Operational (Base CyclePlanner)**

---

*Project: CyclePlanner Conversion to Python*  
*Last Update: 2026-02-18*  
*Version: 1.1 (Phase 1-4 Complete)*
