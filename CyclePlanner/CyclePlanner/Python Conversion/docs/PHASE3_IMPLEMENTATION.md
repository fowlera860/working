# Phase 3 Implementation: Production Orders & Time-Phased Reports

## Overview
Phase 3 implements the production orders and time-phased reporting converters, completing the foundation for CyclePlanner automation.

## Components Created

### 1. production_orders_converter.py
**Purpose**: Extract production order details from PPP010 table

**Key Functions**:
- `build_production_orders_query()` - Builds SQL query with Planning Groups filter
- `fetch_production_orders()` - Executes query against database
- `process_production_orders()` - Adds WeeksOut calculation
- `main()` - Orchestration entry point

**Database Query**:
- Source: `data.PPP010` (Production Planning table)
- Join: Filtered by Planning Groups (Style, Color, Size, Back)
- Filters: Status IN ('O', 'R', 'S') - Open, Ready, Started
- Output Columns: 14 columns including Style, Color, ProdOrderNum, OrderQty, PromiseDate, WeeksOut

**Output**: `production_orders.csv`

---

### 2. time_phase_production_orders_converter.py
**Purpose**: Pivot production orders to weekly format (PD W 01 - PD W 13)

**Key Functions**:
- `create_time_phased_production_orders()` - Pivots OrderQty to weekly columns
- `main()` - Orchestration entry point

**Logic**:
1. Fetch production orders using `production_orders_converter`
2. Process with WeeksOut calculation
3. Group by Style/Color/Size/Back/WeeksOut
4. Pivot quantity to weekly columns (PD W 01...PD W 13)
5. Export with fallback handling

**Pivot Columns**: PD W 01, PD W 02, ..., PD W 13 (13 weeks maximum)

**Output**: `time_phase_production_orders.csv`

---

### 3. time_phase_shipments_converter.py
**Purpose**: Pivot mill orders (shipments) to weekly format (SH W 01 - SH W 13)

**Key Functions**:
- `create_time_phased_shipments()` - Pivots Qty to weekly columns
- `main()` - Orchestration entry point

**Logic**:
1. Fetch mill orders using `mill_orders_converter`
2. Group by Style/Color/Size/Back/WeeksOut
3. Pivot quantity to weekly columns (SH W 01...SH W 13)
4. Export with fallback handling

**Pivot Columns**: SH W 01, SH W 02, ..., SH W 13 (13 weeks maximum)

**Output**: `time_phase_shipments.csv`

---

## Architecture Patterns

### Shared Utilities Used
- `load_config()` - Configuration management
- `load_planning_groups()` - Excel file loading with error handling
- `build_group_filter_cte()` - SQL CTE construction
- `get_weeks_out()` - Week calculation from promise date
- `pivot_to_weeks()` - Pivoting logic for time-phased reports
- `export_with_fallback()` - CSV export with locked file handling
- `ensure_export_folder()` - Directory creation

### Reuse Pattern
- ProductionOrders queries database directly (like Phase 1)
- TimePhaseProductionOrders reuses ProductionOrders data
- TimePhaseShipments reuses MillOrders data via `fetch_all_mill_orders()`
- All use shared utilities for consistency

---

## Test Results

### Test Coverage
All Phase 3 logic validated with mock data:

```
✓ ProductionOrders: 3 records with WeeksOut 2-4 weeks
✓ TimePhaseProductionOrders: 3 style/color combinations with weekly columns
✓ TimePhaseShipments: 3 style/color combinations with weekly columns
```

### Key Validations
1. **WeeksOut Calculation**: Correctly calculates weeks from current Sunday to promise date
2. **Pivot Logic**: Properly distributes quantities into weekly columns
3. **Column Naming**: Follows conventions (PD W 01, SH W 01, etc.)
4. **Data Types**: Numeric aggregation working correctly
5. **Error Handling**: Graceful handling of empty results

---

## Integration with Master Script

### UpdateCyclePlanner.py Updates
Added Phase 3 converters to orchestration:

```python
converters = [
    # Phase 1: Foundation
    (inventory_converter, "Inventory"),
    (product_specs_converter, "Product Specifications"),
    (sales_forecast_converter, "Sales Forecast"),
    # Phase 2: Mill Orders
    (mill_orders_converter, "Mill Orders (Combined)"),
    # Phase 3: Production Orders & Time-Phased
    (production_orders_converter, "Production Orders"),
    (time_phase_production_orders_converter, "Time-Phase Production Orders"),
    (time_phase_shipments_converter, "Time-Phase Shipments")
]
```

Master script now runs 7 converters sequentially with error handling and timing.

---

## File Dependencies

### Module Imports
- `production_orders_converter.py` → `utils.py` (utilities)
- `time_phase_production_orders_converter.py` → `production_orders_converter.py`, `utils.py`
- `time_phase_shipments_converter.py` → `mill_orders_converter.py`, `utils.py`

### Data Flow
```
Excel Files (Planning Groups, Sales Forecast)
    ↓
Config (config.json)
    ↓
[Phase 1 Converters] → CSV outputs
    ↓
[Phase 2 Converters] → CSV outputs
    ↓
[Phase 3 Converters]
├── production_orders_converter → production_orders.csv
├── time_phase_production_orders_converter → time_phase_production_orders.csv
└── time_phase_shipments_converter → time_phase_shipments.csv
```

---

## Output Summary

### Phase 3 CSV Files
1. **production_orders.csv** - One row per production order with details
2. **time_phase_production_orders.csv** - One row per style/color combo with weekly columns (PD W 01-13)
3. **time_phase_shipments.csv** - One row per style/color combo with weekly columns (SH W 01-13)

All exported with fallback naming (timestamp added if file locked).

---

## Remaining Work

### Phase 4: Master Consolidation
- CyclePlannerPrebuild converter (combines all data into comprehensive report)
- SQL-based consolidation of all 7 outputs
- Additional calculations and formatting

### Phase 5+: Specialized Converters
- TuftingOrders
- CombinedOutgoing (already replaced by Phase 2 MillOrders)
- Other secondary reports

---

## Quick Start

### Run All Converters (Including Phase 3)
```bash
python UpdateCyclePlanner.py
```

### Run Phase 3 Only
```bash
python production_orders_converter.py
python time_phase_production_orders_converter.py
python time_phase_shipments_converter.py
```

### Test Phase 3 Logic
```bash
python test_phase3_converters.py
```

---

## Known Patterns

### Week Calculation
- Current week: Sunday start date
- WeeksOut: Max 13 weeks out
- Edge cases: Same day, future dates, past dates handled gracefully

### Pivot Logic
- Groups by Style/Color/Size/Back + source (for shipments)
- Values distributed to appropriate week column
- Missing weeks default to 0.0
- Supports 13 week planning horizon

### Error Handling
- Empty result sets logged with warning, not error
- File locking handled with timestamped fallback
- Column validation before processing
- pyodbc exceptions caught with helpful messages

---

## Success Criteria ✓

- [x] ProductionOrders converter created and tested
- [x] TimePhaseProductionOrders converter created and tested
- [x] TimePhaseShipments converter created and tested
- [x] Mock data tests pass (3/3 test cases)
- [x] UpdateCyclePlanner.py updated with Phase 3
- [x] Documentation complete
- [x] Integration verified (converters load correctly)
- [x] Error handling validated

Phase 3 is **COMPLETE** and ready for database testing.
