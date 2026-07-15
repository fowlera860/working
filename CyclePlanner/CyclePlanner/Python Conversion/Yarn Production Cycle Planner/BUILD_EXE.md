# Building an EXE for Yarn Production Cycle Planner

Both `CAMS` and `CAMSY` connect via SQL Server (ODBC Driver 17+), so a standard **64-bit Python** build is fine.

## 1) Install dependencies

```bash
pip install pyinstaller pandas pyodbc openpyxl
```

## 2) Build executable

From the `Yarn Production Cycle Planner` folder:

```bash
pyinstaller UpdateYarnProductionCyclePlanner.spec
```

## 3) Output

- `dist/UpdateYarnProductionCyclePlanner.exe`

## 4) Deployment

- Keep `config.json` next to the exe — paths and connection settings can be edited without rebuilding.
- ODBC Driver 17 (or later) for SQL Server must be installed on the target machine.

## Notes

- The spec file lists all converter modules as `hiddenimports` so PyInstaller bundles them correctly.
- To add a new converter: add the `.py` file, register it in `UpdateYarnProductionCyclePlanner.py`, and add the module name to `hiddenimports` in the spec.

## Input Files

This model reads from two Yarn Cycle Planner exports:

| Config Key | Path |
|---|---|
| `open_yarn_production_csv` | `\\tdg-sa-file\Atmore\IE\Yarn Cycle Planner\exports\Open Yarn Production.csv` |
| `yarn_order_recommendation_csv` | `\\tdg-sa-file\Atmore\IE\Yarn Cycle Planner\exports\Yarn Order Recommendations.csv` |

And the shared Yarn Alts reference:

| Config Key | Path |
|---|---|
| `yarn_alts_xlsx` | `\\tdg-sa-file\Atmore\IE\Cycle Planner\YarnAlts.xlsx` |
