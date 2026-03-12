# AI Agent Instructions for Working Repository

## Project Overview

This workspace contains **business data automation scripts** that integrate Power Query (Power BI/Excel) and Python to manage production cycles, inventory, forecasting, and tax calculations. The primary data source is the **IMB DB2 Database (TDG-SA-DTS)** and **CAMS database (TDG-DLT-IBMSQL)**.

### Key Components

- **CyclePlanner**: Production cycle planning with inventory management, forecasting, and production order tracking
- **Power Query Files (.pq)**: Queries for Power BI models, structured for direct SQL execution against DB2/SQL Server
- **Python Conversion**: Modernizing Power Query logic to Python with pandas/pyodbc for better maintainability

## Architecture Patterns

### Power Query - SQL Server Direct Query Pattern

All `.pq` files (except those in `Python Conversion/`) follow a **server-side filtering strategy**:

1. **SQL Composition**: Build SQL with parameters directly in the query using `Number.ToText()` for type conversion
2. **CTE Chains**: Complex queries use Common Table Expressions (CTEs) that are composed from referenced queries
3. **Reference Pattern**: Queries reference other queries (e.g., `Inventory.pq` references `Group_Filter_CTE` and `InvRollCutoff`)

**Example from Inventory.pq**:
```powerquery
SQL = Group_Filter_CTE & "
    SELECT F1STYL Style, F1ALTF Feet
    FROM data.FIP010
    WHERE F1ALTF > " & Number.ToText(InvRollCutoff) & "
```

### Critical Conventions

1. **Database Naming**: 
   - DB2 (IBM i): `TDG-SA-DTS` system with `CAMS` database
   - SQL Server: `TDG-DLT-IBMSQL` server with `CAMS` database
   - DB2 files use `FIPxxx` naming (e.g., FIP080, FIP010)

2. **Parameter References**: 
   - `LastDte` - dates for rolling cutoff filters
   - `InvRollCutoff` - minimum feet threshold for inventory (usually 100)
   - `Planning_Groups` - loaded from Excel, drives CTE filtering

3. **Text Trimming**: Always include this step after pulling text data:
   ```powerquery
   TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
   CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))
   ```

## Python Conversion Guidelines

When converting Power Query to Python:

1. **Preserve the Data Pipeline**: Map CTE structure to pandas DataFrames with logical step comments
2. **SQL Composition**: Use `.format()` or f-strings for parameter substitution (matching Power Query's `Number.ToText()`)
3. **Connection String**: Use `pyodbc` with ODBC Driver 17 or higher
4. **Test with Mock Data**: [test_inventory_converter.py](test_inventory_converter.py) demonstrates testing without database

**Python Template** (see [inventory_converter.py](inventory_converter.py)):
```python
def build_cte_query(df, param) -> str:
    # Build VALUES block from DataFrame
    # Return complete SQL string with parameter substitution
    
def fetch_data(planning_groups_df) -> pd.DataFrame:
    # Connect → execute query → return DataFrame
    # Catch pyodbc errors gracefully
```

## Common Tasks

### Refactoring Power Query for Performance

1. **Identify final outputs**: Look for `#"Removed Columns"` or final variable to see what columns are needed
2. **Extract WHERE clauses**: Convert `Table.SelectRows()` to SQL `WHERE` conditions
3. **Replace hierarchical navigation**:
   - ❌ `Odbc.DataSource("dsn=CAMS")[Name="TDGSADTS"][Name="CAMS"]`
   - ✅ `Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL])`

### Python-ifying a Power Query Query

1. Copy the SQL from the `.pq` file
2. Create `build_cte_query()` function that reconstructs the SQL as a string
3. Create `fetch_data()` function using `pyodbc.connect()` and `pd.read_sql()`
4. Add mock data tests before database connectivity

## File Organization

```
CyclePlanner/
├── CyclePlanner/          # Main queries
│   ├── Group_Filter_CTE.pq     # Builds CTE from Planning_Groups
│   ├── Inventory.pq             # Uses Group_Filter_CTE + InvRollCutoff
│   ├── Planning_Groups.pq       # Loads from Excel reference
│   └── Python Conversion/       # Python versions (pandas + pyodbc)
│       ├── inventory_converter.py
│       └── test_inventory_converter.py
```

## Important References

- **Connection Details**: See README.md for ODBC driver configuration
- **PowerQuery Standard Template**: In README.md - copy for new queries
- **Database Schema**: Tables are in `data.` schema (e.g., `data.FIP010`)
- **Excel Parameters**: Stored in referenced Excel files (Planning Groups.xlsx, etc.)

## Known Patterns

- **Mixed DB2/SQL Server**: Some queries pull from DB2 (`TDG-SA-DTS`), others from SQL Server (`TDG-DLT-IBMSQL`)
- **Parameter Chaining**: `Inventory.pq` → depends on `Group_Filter_CTE` → depends on `Planning_Groups` + `InvRollCutoff`
- **CTE Composition**: CTEs are built as strings and concatenated to prevent reevaluation
