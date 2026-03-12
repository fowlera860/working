# Greige Download VBA → Power Query Migration Plan

## Executive Summary

This document outlines the plan to migrate the legacy `DLINV.vba` script to a modern Power Query solution. The current VBA is a collection of three subroutines with unclear purposes and hardcoded logic. The new approach will be modular, maintainable, and user-driven.

---

## Current State Analysis

### What the VBA Does (Decoded)

The code contains **three separate operations**:

#### 1. **`Inventory()` Subroutine** — Main Greige Inventory Download
- **Purpose**: Pull greige (undyed fabric) roll inventory from DB2 system (CAMS database, GIP010 table)
- **Data Sources**: 
  - `CAMS.GIP010` (Greige Inventory Ledger)
  - `CAMS.YAP070` (WIP - Work in Progress)
- **Output Structure**: Multiple side-by-side columns (A-AG range), each representing a different inventory category:
  - **Cols A-C**: 1st Quality Rolls (Atmore warehouse)
  - **Cols E-G**: Fabrica Inventory (WH 39/59, Quality 7 & 5 excluded)
  - **Cols I-K**: Quality 7 Rolls
  - **Cols Q-S**: Quality 5 Rolls
  - **Cols X-Y**: 2nd Quality Rolls
  - **Cols AF-AG**: WIP Yardage (from YAP070)

**Quality Filters**:
- Excludes: Dead rolls (G1ACT=7 or 9), lost inventory, specific warehouses (37, 59)
- Includes: Rolls >25 ft length, no color, no dead date
- **Data Calculations**: Converts dimensions (feet + inches) to square yards using formula: `((Length*12 + inches) * (Width*12 + inches)) / 1296`

---

#### 2. **`DownloadSalesGreigeAndInv()` Subroutine** — Sales & Weekly Usage
- **Purpose**: Create a mapping of styles to weekly usage (sales forecast)
- **User Input**: Reads style list from "Inventory" sheet (cells A5+)
- **Process**:
  - Creates temporary DB2 tables/views to track style variants
  - Joins sales data (SAP400 table) with style input
  - Calculates weekly usage by summing sales yardage divided by 13 weeks
  - Some complex logic around style aliases (primary vs. alternate styles)
- **Output**: "Data" sheet, columns U-V (Style, Weekly Usage)
- **Artifacts**: **WE'RE REMOVING THIS** — user says no more week-over-week info

---

#### 3. **`SalesData()` Subroutine** — Style Categorization
- **Purpose**: Cross-reference styles against two lookup lists to apply business rules:
  - **Sample Styles**: Mark styles that are samples (test/trial products)
  - **Drop Listed**: Mark styles being discontinued
  - **Otherwise**: Populate with sales figures
- **Input**: 
  - Sales data from "DATA" sheet (cols U-V)
  - Sample styles list (Tables sheet, A3+)
  - Drop list (Tables sheet, D3+)
  - Artificial demand overrides (Tables sheet, N3+)
- **Output**: Column G in "INVENTORY" sheet (categorization: "Samples", "Drop Listed", or sales value)
- **Special Logic**: Some hardcoded style merging (9390+9411→Tocarres, 9352+7214→Bandala, etc.)

---

## New Architecture

### Sheet Structure (4 sheets)

#### **1. CONFIG Sheet** (Editable Parameters)
- **Purpose**: Centralized configuration for all operational parameters
- **Format**: Key-Value pairs (two columns: Parameter, Value)
- **Contents**:
  - `Min_Roll_Length_FT` → 25
  
**Design Note**: Minimal configuration needed. Quality grades are fixed (1, 7, and "other" always included; 9 always excluded). All location filtering removed - inventory pooled across all facilities.

**Quality Rules** (hardcoded in queries):
- Quality 1: 1st quality rolls → `Inv.` column
- Quality 7: Quality 7 rolls → `Quality 7 Inv.` column  
- Quality 2,3,4,6,8: Other qualities → `Quality 2,3,4,6,8 & 9 Inv.` column
- Quality 5: TBD (doesn't fit report categories)
- Quality 9: Always excluded (deleted/shipped rolls)

---

#### **2. INPUT Sheet** (User-Maintained)
- **Purpose**: Central style management
- **Columns**:
  - `Style` — 5-character style code (primary key)
  - `Notes` — Free-form notes field (optional)
  - **Read-only data**: Inventory data will be lookup-joined from REPORT
  
**Design Note**: Simple, clean, minimal maintenance

---

#### **3. REPORT Sheet** (Auto-Generated Inventory)
- **Purpose**: Comprehensive inventory status for all tracked styles
- **Data Refresh**: Power Query queries pull latest from DB2
- **Columns** (inventory-focused):
  
  | Column | Source | Notes |
  |--------|--------|-------|
  | Style, Name, Notes | INPUT sheet lookup | User-maintained metadata |
  | Inv. | GIP010, Quality=1 | SQYD (1st quality, all facilities pooled) |
  | Rolls | GIP010, Quality=1 | Roll count (1st quality, all facilities pooled) |
  | Quality 7 Inv. | GIP010, Quality=7 | SQYD (quality 7, all facilities pooled) |
  | Quality 2,3,4,6,8 & 9 Inv. | GIP010, Quality∈{2,3,4,6,8} | SQYD (other qualities, pooled; excludes Q5 & Q9) |
  | (Other columns) | External sources | Not part of Greige Download scope |

**Design Principle**: All inventory pooled across facilities (Atmore, California, etc.) - no location-level breakdown needed.

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Goal**: Create workbook structure, CONFIG sheet, and test DB connectivity

1. **Create workbook structure**
   - New Excel file with CONFIG, INPUT, REPORT sheets
   - CONFIG sheet: Key-value parameter table
     - Min_Roll_Length_FT = 25
   - INPUT sheet: Simple table with headers (Style, Name, Notes)
   - Add 5-10 sample styles from current data

2. **Create helper query for CONFIG**
   - `Q_Config` — reads CONFIG sheet, returns all parameters as a record
   - All downstream queries reference this (not hardcoded values)

3. **Test modern DB connection**
   - Replace ODBC DSN (`IBMDA400`) with modern ODBC driver string
   - Test connection in Power Query (use `Sql.Database()` or `Odbc.Query()` with explicit driver)
   - Create a small test query to pull style inventory from GIP010

4. **Deliverables**:
   - ✅ Excel workbook scaffolding (3 sheets: CONFIG, INPUT, REPORT)
   - ✅ CONFIG sheet populated with key parameters
   - ✅ Working Power Query to DB2 using modern driver
   - ✅ Q_Config helper query
   - ✅ Sample data in INPUT sheet (user-maintained style list)

---

### Phase 2: Core Inventory Queries (Week 2)
**Goal**: Build Power Query queries for each quality grade (reading from CONFIG)

1. **Create separate queries for each quality grade**
   - All queries will call `Q_Config` first to get Min_Roll_Length_FT
   - `Q_Inventory_Quality1` — GIP010 where Quality=1 (all facilities pooled)
   - `Q_Inventory_Quality7` — GIP010 where Quality=7 (all facilities pooled)
   - `Q_Inventory_OtherQualities` — GIP010 where Quality∈{2,3,4,6,8} (pooled)
   
   **Note**: Quality 9 always excluded (deleted/shipped rolls). Quality 5 TBD - not included yet.

2. **Common SQL filters** (applied to all queries):
   - Exclude dead/shipped rolls: `G1ACT NOT IN (7, 9)`
   - Exclude deleted/shipped quality: `G1QLTY <> 9`
   - Exclude lost inventory: `G1LOC <> 'LOST'`
   - No color: `G1CLR = ''`
   - Minimum length: `G1CLTF >= [Min_Roll_Length_FT]` (from CONFIG)
   - No dead date: `G1DDTE < 1`
   - Other filters: `G1SCLR < '1'`, `G1DPRT <> 'Y'`, `G1DLOT < '1'`, `G1ATLF > 1`

3. **Each query should**:
   - Read from Q_Config for parameters (min length, quality toggles)
   - Use direct SQL (not hierarchical navigation)
   - Apply common filters + quality filter in WHERE clause
   - Calculate SQYD using formula: `ROUND(SUM(((G1CLTF*12 + G1CLTI) * (G1CWTF*12 + G1CWTI)) / 1296), 0)`
   - Group by Style and return (Style, SQYD, Rolls)
   - Trim all text columns

4. **Deliverables**:
   - ✅ Three independent, reusable queries (using CONFIG for roll length threshold)
   - ✅ Each tested with sample data
   - ✅ Quality grades hardcoded per business rules (1, 7, and 2/3/4/6/8)

---

### Phase 3: Combine & Map to INPUT (Week 3)
**Goal**: Build the REPORT sheet by joining all inventory to the INPUT style list

1. **Create `Q_Report` query**
   - Start with INPUT sheet (list of managed styles)
   - Left join each inventory query by Style (only those enabled in CONFIG)
   - If no match, show 0 or null
   - Add calculated Total_SQYD column
   - Flatten to single table

2. **Load into REPORT sheet**
   - Set connection to refresh on open
   - Allow manual refresh button

3. **Deliverables**:
   - ✅ REPORT sheet auto-populated with joined data
   - ✅ Null handling (styles in INPUT but not in inventory show 0)
   - ✅ Dynamic columns based on CONFIG (don't show disabled quality grades)

---

### Phase 4: Unmatched Styles Report (Week 4)
**Goal**: Build quality control report of styles in DB but not managed

1. **Create `Q_Unmatched` query**
   - Union all inventory queries (all styles found)
   - Exclude styles in INPUT sheet
   - Result: list of "orphaned" styles
   - Optional: Show which categories each style appears in

2. **Load into UNMATCHED sheet**
   - Allows user to quickly identify missing configs
   - Can serve as discovery tool

3. **Deliverables**:
   - ✅ UNMATCHED sheet with auto-generated orphan list
   - ✅ User can add styles to INPUT and refresh

---

### Phase 4: Cleanup & Optimization (Week 4)
**Goal**: Polish, document, and handle edge cases

1. **Error handling**
   - DB connection failures → friendly message
   - Missing data → proper nulls, not errors

2. **Performance**
   - Test with full DB (1000s of styles)
   - Optimize queries if needed (add indexes, prefilters)

3. **Documentation**
   - Add comments to each Power Query
   - Create user guide for INPUT sheet maintenance
   - Document refresh schedule/process

4. **Decommission**
   - Archive the old DLINV.vba workbook
   - Remove all references to it

5. **Deliverables**:
   - ✅ Final, tested workbook
   - ✅ User documentation

---

### 1. Connection Method
**Current**: ODBC DSN (IBMDA400, hard to maintain)
**Proposed**: Modern ODBC driver with explicit connection string
```powerquery
Odbc.Query(
    "Driver={IBM i Access ODBC Driver};System=TDG-SA-DTS;DBQ=CAMS;...",
    SQL_String
)
```
**Benefit**: No DSN dependency, clearer in code, easier to change servers

---

### 2. Modularity & Configuration
**Current**: Single VBA sub with hardcoded warehouse numbers and quality thresholds
**Proposed**: Separate Power Query for each quality grade, with parameters in CONFIG sheet. All locations pooled.
**Benefit**: 
- Easy to test/debug each quality grade
- Reusable (can query Quality 1 separately from Quality 7)
- Maintainable (one change doesn't break others)
- **User-editable**: Toggle quality grades or adjust thresholds without touching SQL
- **Simplified**: No location-level filtering needed (WH 37/39 removed, all inventory pooled)

---

### 3. User Input & Report Scope
**Current**: 
- User maintains INVENTORY sheet (column A, row 5+) with style list
- Inventory() pulls ALL styles from DB regardless of input list
- SalesData() and report only show INPUT list styles
**Proposed**: 
- User maintains INPUT sheet (table) with Style, Name, Notes
- REPORT only includes styles from INPUT sheet (explicit, user-driven)
- Inventory queries pull only for styles in INPUT (more efficient)
- No "unmatched styles" report needed — only INPUT styles are tracked

---

### 4. What Gets Removed
- ✅ `DownloadSalesGreigeAndInv()` — No more weekly usage lookup
- ✅ `SalesData()` logic — No more style categorization (Samples/Drops)
- ✅ Hardcoded style combinations (Tocarres, Bandala, Texere, etc.)
- ✅ Temporary table creation (QTEMP)
- ✅ ODBC DSN dependency

---

## Questions to Clarify

1. **WIP Data**: The VBA pulls WIP from YAP070 (columns AF-AG). Should this feed the report, or is it used elsewhere?

2. **Refresh Cadence**: How often should this auto-refresh? On file open? Daily? Manual only?

3. **Name Column**: Should the INPUT sheet include a Style Name/Description field, or just Style + Notes?

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| DB2 schema changes | Document current schema, add comments in SQL with table names |
| Performance with large style list | Test with 1000+ styles, consider batch loading |
| User confusion with INPUT sheet | Clear instructions, example data, data validation |
| Connection failures | Add error handling, clear error messages |
| Warehouse/quality filter changes | Move to configurable INPUT table instead of hardcoding |

---

## Success Criteria

- ✅ Modern ODBC connection (no DSN)
- ✅ 3-sheet structure (CONFIG, INPUT, REPORT)
- ✅ All legacy SQL logic captured in Power Query
- ✅ Week-over-week logic completely removed
- ✅ REPORT auto-updates within 2 minutes
- ✅ User can add/remove styles in INPUT and see them in REPORT after refresh
- ✅ Zero VBA dependencies
- ✅ Clear documentation

---

## Timeline

| Phase | Duration | Owner |
|-------|----------|-------|
| Phase 1: Foundation | 3 days | AI |
| Phase 2: Core Queries | 4 days | AI |
| Phase 3: Combine & Map | 3 days | AI |
| Phase 4: Cleanup & Docs | 2 days | AI + User |
| **Total** | **~2 weeks** | |

---

## Next Steps

1. **Confirm** the simplified plan (only INPUT-driven, no unmatched styles sheet)
2. **Clarify** remaining questions (WIP data, refresh cadence, Name column)
3. **Provide** 5-10 sample styles to populate INPUT sheet
4. **Begin** Phase 1: Foundation (create workbook structure)
