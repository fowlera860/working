# CyclePlanner Python Conversion Plan

## Overview
This document outlines the complete conversion of all Power Query files in the CyclePlanner folder to Python scripts with SQL database integration and CSV exports.

## File Dependency Tree

```
Planning_Groups (Excel)
    ↓
Group_Filter_CTE (builds SQL CTE from Planning_Groups)
    ↓
    ├─→ Product_Specs.pq
    │
    ├─→ MillOrderProductionAssignment.pq ─────┐
    ├─→ UnassignedMillOrders.pq ───────────┬──┤→ MillOrders (combined)
    └─→ MillOrderRollAssignment.pq ─────────┘  │
                                                ├─→ TimePhaseShipments.pq
                                                │
    ├─→ ProductionOrders.pq ──────────────────→ TimePhaseProductionOrders.pq
    │
    ├─→ Inventory.pq ✓ (DONE)
    │
    └─→ SalesForecast.xlsx ──→ SalesForecast.pq

CyclePlannerPrebuild (combines all above)
    ├─ Product_Specs
    ├─ MillOrders (MillOrderProductionAssignment + UnassignedMillOrders + MillOrderRollAssignment)
    ├─ Inventory
    ├─ SalesForecast
    ├─ TimePhaseProductionOrders
    ├─ TimePhaseShipments
    └─ fnTimePhasedInventory (custom function)
```

## Files to Convert

### Phase 1: Foundation Files (No Dependencies)
These can be converted independently.

#### 1. **Product_Specs** → `product_specs_converter.py`
**Source:** Product_Specs.pq
**Dependencies:** 
- Group_Filter_CTE (SQL CTE pattern)
- Database: CAMS

**Logic:**
- Build CTE from Planning_Groups
- Join multiple DB2 tables: FIP020, FIP020B, FIP712, FIP715, GIP030
- Extract product specifications
- Sort and reorder columns

**Key SQL Operations:**
- DISTINCT rows
- Multiple INNER/LEFT OUTER JOINs
- Filter on MASTER='Y' and APPVD='Y'

**Output:** CSV with columns:
`PlanningGroup, ColorGroup, Style, StyleName, Color, ColorName, Size, Back, RollSize, FaceWt, MachineNum, MachineDescription, EPN`

---

#### 2. **SalesForecast** → `sales_forecast_converter.py`
**Source:** SalesForecast.pq + SalesForecast.xlsx
**Dependencies:**
- SalesForecast.xlsx file
- Planning_Groups.xlsx file (for inner join)

**Logic:**
- Load SalesForecast table from Excel
- Remove 26-week columns (keep only forecast columns)
- Type conversions (text/number)
- Inner join with Planning_Groups
- Expand planning group columns

**Key Operations:**
- Excel table load with column filtering
- Inner join with Planning_Groups
- Table expansion

**Output:** CSV with columns:
`Style, Color, Size, Back, FC W 01...FC W 12, PlanGroup, ColorGroup`

---

### Phase 2: Database Query Files (Uses CTE)
These depend on Group_Filter_CTE pattern.

#### 3. **MillOrderProductionAssignment** → `mill_orders_converter.py`
**Source:** MillOrderProductionAssignment.pq
**Dependencies:** Group_Filter_CTE, Database: CAMS

**Logic:**
- Build CTE from Planning_Groups
- Query PRP010 (Production Records)
- Left outer join with FIP010 (Inventory)
- Calculate RsvQty (sum of reserved feet)
- Calculate PendingProd (Assigned - Reserved)
- Add source column: "Production Assignment"

**Key SQL Operations:**
- GROUP BY with SUM aggregation
- CASE statement for PendingProd calculation
- Null handling with ISNULL

**Output:** Columns:
`Style, Color, Size, Back, OrdNum, OrdLine, ProdOrder, AsgQty, PromDt, RsvQty, PendingProd, Src`

---

#### 4. **MillOrderRollAssignment** → `mill_orders_converter.py`
**Source:** MillOrderRollAssignment.pq
**Dependencies:** Group_Filter_CTE, Database: CAMS

**Logic:**
- Build CTE from Planning_Groups
- Query FIP010 (Inventory - assigned rolls)
- Left outer join with OPP010 (Orders)
- Filter on activity status (F1ACT < 7)
- Add source column: "Roll Reserve"

**Output:** Columns:
`Style, Color, Size, Back, OrdNum, OrdLine, Qty, PromDt, Src`

---

#### 5. **UnassignedMillOrders** → `mill_orders_converter.py`
**Source:** UnassignedMillOrders.pq
**Dependencies:** Group_Filter_CTE, Product_Specs (for RollSize), Database: CAMS

**Logic:**
- Build CTE from Planning_Groups
- Query OPP010 (Orders table)
- Filter: unassigned orders (O1CNCD=0, O1OCJL=0, etc.)
- NOT EXISTS: exclude orders already in production
- Left join with Product_Specs (for RollSize)
- Calculate LF (Linear Feet) = Qty × RollSize if UOM='RL', else Qty
- Add source column: "Unassigned"

**Output:** Columns:
`Style, Color, Size, Back, OrdNum, OrdLine, Qty, UOM, PromDt, LF, Src, RollSize`

---

#### 6. **MillOrders (COMBINED)** → `mill_orders_converter.py`
**Combines:** MillOrderProductionAssignment + MillOrderRollAssignment + UnassignedMillOrders
**Replaces:** CombinedOutgoing.pq

**Logic:**
1. Fetch all three datasets above
2. Combine tables (UNION)
3. Add WeeksOut calculation:
   - Current week = Sunday of current week
   - WeeksOut = (PromDt - CurrentWeekSunday) / 7
   - If <= 0, set to 1
4. Reorder columns for consistency

**Output:** Combined CSV with all three sources

---

#### 7. **ProductionOrders** → `production_orders_converter.py`
**Source:** ProductionOrders.pq
**Dependencies:** Group_Filter_CTE, Database: CAMS

**Logic:**
- Build CTE from Planning_Groups
- Query PPP010 (Production Orders table)
- Filter: PPCOMP ≠ 'Y' (incomplete only)
- Get only latest sequence (PPSEQ# = MAX)
- Type convert ProdDate, PromDate to dates
- Add WeeksOut calculation (same as MillOrders)

**Output:** Columns:
`Style, Color, Size, Back, ProdNum, FtOrdered, ProdDate, PromDate, WH, WeeksOut`

---

### Phase 3: Transformation Files (Pivot/Reshape)

#### 8. **TimePhaseProductionOrders** → `time_phase_production_orders_converter.py`
**Source:** ProductionOrders output
**Dependencies:** ProductionOrders

**Logic:**
1. Remove columns: ProdNum, ProdDate, WH
2. Filter rows where WeeksOut >= 1 and WeeksOut <= 13
3. Create dummy rows for all weeks 1-13 with 0 values
4. Combine real data with dummy rows
5. Transform WeeksOut to text format: "PD W 01", "PD W 02", etc.
6. Pivot table on WeeksOut column, summing FtOrdered
7. Replace nulls with 0
8. Reorder columns in week sequence
9. Filter out rows where Style = 0

**Output:** CSV with columns:
`Style, Color, Size, Back, PD W 01, PD W 02, ..., PD W 13`

---

#### 9. **TimePhaseShipments** → `time_phase_shipments_converter.py`
**Source:** MillOrders output
**Dependencies:** MillOrders

**Logic:**
1. Remove unnecessary columns (Src, OrdNum, OrdLine, UOM, PromDt, Product_Specs.RollSize, LF, ProdOrder, AsgQty, RsvQty, PendingProd)
2. Filter rows where WeeksOut >= 1 and WeeksOut <= 13
3. Rename Qty to FtToShip
4. Create dummy rows for all weeks 1-13 with 0 values
5. Transform WeeksOut to text format: "SH W 01", "SH W 02", etc.
6. Pivot table on WeeksOut column, summing FtToShip
7. Replace nulls with 0
8. Reorder columns in week sequence
9. Filter out rows where Style = 0

**Output:** CSV with columns:
`Style, Color, Size, Back, SH W 01, SH W 02, ..., SH W 13`

---

### Phase 4: Complex Master File

#### 10. **CyclePlannerPrebuild** → `cycle_planner_prebuild_converter.py`
**Source:** CyclePlannerPrebuild.pq
**Dependencies:** ALL files above

**Logic:**
This is the master consolidation file. It:
1. Loads Product_Specs
2. Nested join (left outer) with MillOrders:
   - Sum [PendingProd] → AsgQty
   - Sum [RsvQty] → ReservedQty
3. Nested join with MillOrders (unassigned only):
   - Calculate B/O: if UOM='RL' then RollSize × Qty else Qty
   - Sum → B/O
4. Nested join with Inventory:
   - Sum [Feet] → OnHand
5. Nested join with SalesForecast:
   - Keep all columns
6. Nested join with TimePhaseProductionOrders:
   - Keep all week columns
7. Nested join with TimePhaseShipments:
   - Keep all week columns
8. Replace null OnHand with 0
9. Add TimePhase column:
   - Call fnTimePhasedInventory function
   - Calculates cumulative inventory for weeks 1-12
10. Expand TimePhase record to columns (Week 01...Week 12)
11. Add AvgForecast (average of FC W 01...12)
12. Reorder and remove unnecessary columns

**Output:** Master CSV with all planning data

---

### Phase 5: Yarn Cycle Planner Extension

#### 11. **YarnAlts (Excel Input)**
**Source:** YarnAlts.xlsx (single table)
**Columns:** BaseType, BaseColor, AltNum, AltType, AltColor, AltSupplier

**Logic:**
- Load YarnAlts table from Excel
- Trim text columns
- Validate required columns

**Output:** DataFrame used for yarn mapping

---

#### 12. **YarnXRef (Extend Existing Converter)**
**Source:** YarnXRef.pq / existing converter
**Change:** Add `YarnColor` to the output

**Logic:**
- Ensure each SKU (Style, Color, Size) has at least one yarnxref element
- Preserve current join/filters; add missing color column

**Output:** Extended `yarnxref` data with YarnColor

---

#### 13. **Cycle Planner Yarn Demand** → `cycle_planner_yarn_demand_converter.py`
**Dependencies:** YarnAlts + YarnXRef + CyclePlanner outputs

**Normalization Rules:**
- If `YarnType`/`YarnColor` matches an `AltType`/`AltColor`, map to `BaseType`/`BaseColor`
- Otherwise use values from `yarnxref`

**Planned Output Columns:**
- BaseType, BaseColor, AltType, AltColor, AltSupplier
- SKU count
- Time-phased demand (YR W 01...YR W 20) in lbs

**Output:** `cycle_planner_yarn_demand.csv`

---

## Implementation Steps

### Step 1: Setup & Configuration
- [x] Config.json with paths and sheet names
- [x] Helper script for Excel sheet inspection
- [ ] Update config with all Excel sheet names for SalesForecast

### Step 2: Create Supporting Utilities
- [ ] Create `utils.py` with:
  - `load_config()` - already in inventory_converter
  - `build_group_filter_cte()` - builds CTE from Planning_Groups
  - `get_weeks_out()` - calculates WeeksOut from PromDt
  - `pivot_weeks()` - pivots data for time-phased reports
  - Database connection helper functions

### Step 3: Conversion Sequence (Recommended Order)

**3a. Product_Specs** (Foundation, no other dependencies)
```
product_specs_converter.py
  → Output: product_specs.csv
```

**3b. SalesForecast** (Foundation, no DB dependencies)
```
sales_forecast_converter.py
  → Output: sales_forecast.csv
```

**3c. MillOrders** (Creates 3 files, combines them)
```
mill_orders_converter.py
  → Output: mill_orders_production_assignment.csv
  → Output: mill_orders_roll_assignment.csv
  → Output: mill_orders_unassigned.csv
  → Output: mill_orders.csv (combined)
```

**3d. ProductionOrders**
```
production_orders_converter.py
  → Output: production_orders.csv
```

**3e. TimePhaseProductionOrders**
```
time_phase_production_orders_converter.py
  → Reads: production_orders.csv
  → Output: time_phase_production_orders.csv
```

**3f. TimePhaseShipments**
```
time_phase_shipments_converter.py
  → Reads: mill_orders.csv
  → Output: time_phase_shipments.csv
```

**3g. CyclePlannerPrebuild**
```
cycle_planner_prebuild_converter.py
  → Reads: all CSVs from above
  → Output: cycle_planner_prebuild.csv
```

### Step 4: Testing & Validation
- Mock data tests for each converter
- Compare row counts with Power Query outputs
- Validate column data types and formats
- Check aggregation calculations (sums, averages)

---

## Configuration Updates Needed

Update `config.json` to include:

```json
{
  "excel_sheets": {
    "sales_forecast_sheet": "SalesForecast",  // Verify actual sheet name
    "yarn_alts_sheet": "YarnAlts"            // Single-table workbook
  },
  "output_files": {
    "product_specs": "product_specs.csv",
    "sales_forecast": "sales_forecast.csv",
    "mill_orders": "mill_orders.csv",
    "production_orders": "production_orders.csv",
    "time_phase_production_orders": "time_phase_production_orders.csv",
    "time_phase_shipments": "time_phase_shipments.csv",
    "cycle_planner_prebuild": "cycle_planner_prebuild.csv",
    "cycle_planner_yarn_demand": "cycle_planner_yarn_demand.csv"
  }
}
```

---

## Key Technical Patterns

### 1. Group Filter CTE Pattern
All database queries use a CTE built from Planning_Groups:
```python
def build_group_filter_cte(planning_groups_df):
    """Build VALUES clause for CTE filtering"""
    rows = []
    for _, row in planning_groups_df.iterrows():
        values = [str(val) for val in row]
        row_str = "('" + "','".join(values) + "')"
        rows.append(row_str)
    
    values_block = ",\n".join(rows)
    return f"""
WITH FilterList AS (
    SELECT *
    FROM (VALUES
{values_block}
    ) AS v(style, color, size, back, planningGroup, colorGroup)
)"""
```

### 2. WeeksOut Calculation Pattern
Used in multiple files:
```python
def get_weeks_out(prom_date):
    """Calculate weeks from current week to promise date"""
    today = datetime.now().date()
    current_week_sunday = today - timedelta(days=today.weekday() + 1)
    weeks_diff = (prom_date - current_week_sunday).days // 7
    return 1 if weeks_diff <= 0 else weeks_diff
```

### 3. Pivot to Time-Phased Pattern
Used in TimePhase converters:
```python
def pivot_to_weeks(df, value_col, weeks=13, prefix=""):
    """Pivot data into week columns (W 01...W 13)"""
    # Add dummy rows for all weeks
    # Create week text column
    # Pivot and fill nulls with 0
    # Reorder columns
```

### 4. Nested Join Pattern (for CyclePlannerPrebuild)
```python
# Instead of nested joins (slow in pandas):
# Use merge() with suffixes and concat/groupby for aggregations
```

---

## Error Handling Strategies

1. **Excel File Issues:** Use list_excel_sheets.py helper
2. **Database Connection:** Retry with ODBC driver versions
3. **File Locking:** Fallback to timestamped filenames (already implemented)
4. **Missing Data:** Use proper null handling (pd.isna, fillna)
5. **Type Mismatches:** Validate column types after reads

---

## Performance Considerations

1. **Database Queries:** Use WHERE clauses server-side, not pandas filtering
2. **Large CTEs:** Limit Planning_Groups to active groups only
3. **Pivoting:** pandas pivot can be slow with many rows - consider chunking
4. **File I/O:** Compress CSVs if storage is concern
5. **Caching:** Consider caching Planning_Groups between runs

---

## Rollout Timeline

- **Week 1:** Convert Product_Specs + SalesForecast
- **Week 2:** Convert MillOrders (3 files) + testing
- **Week 3:** Convert ProductionOrders + TimePhase files
- **Week 4:** Combine all into CyclePlannerPrebuild
- **Week 5:** Testing, validation, deployment

---

## Questions to Answer Before Starting

1. What is the actual sheet name in SalesForecast.xlsx?
2. Should converters run independently or as one master script?
3. How often will these run? (Daily? On-demand?)
4. Should we maintain CSVs as intermediate outputs or keep only final file?
5. Are there any data quality rules (min/max values, required fields)?
