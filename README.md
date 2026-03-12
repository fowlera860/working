# Working Files - AI Agent Support Workspace

This workspace is dedicated to providing AI agent support for work-based files including PowerQuery, VBA, and other business automation scripts. The primary purpose is to facilitate refactoring, optimization, and maintenance of existing code through AI assistance.

## Workspace Structure

```
/workspaces/working/
├── 401k/                    # 401k projection queries
├── CyclePlanner/            # Production cycle planning queries
├── Overtime Tax/            # Overtime tax calculation scripts
├── Rebates/                 # Rebate processing queries
├── Roll Testing/            # Roll testing and quality control queries
├── Sales BI/                # Sales business intelligence queries
├── tax-overtime/            # Overtime tax documentation and queries
└── waste project/           # Waste tracking and reporting
```

## PowerQuery Standard Format

All PowerQuery files that pull from the IMB DB2 Database TDG-SA-DTS should follow this optimized format for better performance and maintainability:

### Standard Template

```powerquery
let
    SQL = "
        SELECT  Column1, Column2, Column3
        FROM TableName
        WHERE FilterColumn >= " & Number.ToText(ParameterValue) & "
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))

in
    CleanSource
```

### Key Principles

1. **Direct SQL Queries**: Use `Odbc.Query()` with direct SQL instead of hierarchical navigation through ODBC data sources
2. **Server-Side Filtering**: Apply WHERE clauses in SQL rather than using `Table.SelectRows()` in PowerQuery
3. **Column Selection**: Select only needed columns in the SQL SELECT statement instead of removing columns later
4. **Text Trimming**: Automatically trim all text columns to clean up data
5. **Simplified Structure**: Eliminate unnecessary intermediate variables

### Example: Before and After

**Before (Inefficient)**:
```powerquery
let
    Source = Odbc.DataSource("dsn=CAMS", [HierarchicalNavigation=true]),
    TDGSADTS_Database = Source{[Name="TDGSADTS",Kind="Database"]}[Data],
    CAMS_Schema = TDGSADTS_Database{[Name="CAMS",Kind="Schema"]}[Data],
    FIP080_Table = CAMS_Schema{[Name="FIP080",Kind="Table"]}[Data],
    #"Filtered Rows" = Table.SelectRows(FIP080_Table, each [F8JUL] >= LastDte),
    #"Removed Columns" = Table.RemoveColumns(#"Filtered Rows",{"F8STYL", "F8CLR"})
in
    #"Removed Columns"
```

**After (Optimized)**:
```powerquery
let
    SQL = "
        SELECT  F8ROLL, F8GROL, F8DATE, F8JUL
        FROM FIP080
        WHERE F8JUL >= " & Number.ToText(LastDte) & "
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))

in
    CleanSource
```

## Instructions for AI Agents

### When Refactoring PowerQuery Files:

1. **Identify Required Columns**: Look for the final step in the query (usually `#"Reordered Columns"`, `#"Removed Columns"`, or the final output) to determine which columns are actually needed

2. **Identify Filters**: Check for `Table.SelectRows()` operations and convert them to SQL WHERE clauses

3. **Use the Standard Template**: Replace hierarchical navigation with direct SQL queries

4. **Handle Parameters**: 
   - Parameters like `LastDte` are references to other queries
   - Use `Number.ToText()` to convert numeric parameters for SQL string concatenation
   - Use single quotes for string literals in SQL: `'VALUE'`

5. **Preserve Logic**: Ensure all filtering and selection logic is maintained, just moved to SQL for better performance

6. **Exclude Calculated Columns**: Do not include Excel calculated columns in the SQL SELECT statement

### Database Connection Details

- **System**: TDG-SA-DTS
- **Database**: CAMS
- **Driver**: Client Access ODBC Driver (32-bit)

### Common Patterns

- **Date Filtering**: `WHERE DateColumn >= " & Number.ToText(LastDte) & "`
- **Multiple Conditions**: Use AND/OR in SQL WHERE clause
- **String Comparison**: Use single quotes in SQL: `WHERE Code = 'LOC'` or `WHERE Code <> 'LOC'`
- **Numeric Comparison**: Direct comparison: `WHERE Amount = 0`

## Working with This Workspace

This codespace is specifically configured to assist with:
- Refactoring legacy PowerQuery code
- Optimizing query performance
- Standardizing code format across projects
- Documenting business logic
- VBA script maintenance (future)

## Notes

- Always test refactored queries in Excel/Power BI before deploying to production
- Some queries may reference Excel tables or named ranges (e.g., `LastDte`)
- Preserve all business logic when refactoring - performance improvements should not change results
- When in doubt about column requirements, check the final transformation step in the original query

---

*This workspace is maintained for AI-assisted code improvement and should not contain sensitive production data.*