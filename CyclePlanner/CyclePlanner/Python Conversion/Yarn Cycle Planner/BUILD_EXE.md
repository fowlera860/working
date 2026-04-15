# Building an EXE for Yarn Cycle Planner

Both `CAMS` and `CAMSY` connect via SQL Server (ODBC Driver 17+), so a standard **64-bit Python** build is fine.

## 1) Install dependencies

```bash
pip install pyinstaller pandas pyodbc openpyxl
```

## 2) Build executable

From the `Yarn Cycle Planner` folder:

```bash
pyinstaller UpdateYarnCyclePlanner.spec
```

## 3) Output

- `dist/UpdateYarnCyclePlanner.exe`

## 4) Deployment

- Keep `config.json` next to the exe — paths and connection settings can be edited without rebuilding.
- ODBC Driver 17 (or later) for SQL Server must be installed on the target machine.

## Notes

- The spec file lists all converter modules as `hiddenimports` so PyInstaller bundles them correctly.
- To add a new converter: add the `.py` file, register it in `UpdateYarnCyclePlanner.py`, and add the module name to `hiddenimports` in the spec.
