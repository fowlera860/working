# Building a 32-bit EXE for Yarn Cycle Planner

This project uses an IBM i ODBC driver configured as **32-bit**.
The executable must be built with **32-bit Python**.

## 1) Install 32-bit Python

Install a 32-bit Python version on Windows (same major/minor version used for development).

Quick verification:
```bash
python -c "import struct; print(struct.calcsize('P') * 8)"
```
Expected output: `32`

## 2) Install dependencies in the 32-bit environment

```bash
pip install pyinstaller pandas pyodbc openpyxl
```

## 3) Build executable

From the `Yarn Cycle Planner` folder:

```bash
pyinstaller UpdateYarnCyclePlanner.spec
```

## 4) Output

- `dist/UpdateYarnCyclePlanner.exe`

## 5) Runtime safety check

`UpdateYarnCyclePlanner.py` includes a guard:
- If `CAMSY` uses a `32-bit` ODBC driver and runtime is 64-bit, it exits with a clear error.

## Notes

- Do not build this exe from a 64-bit Python install.
- IBM i / Client Access ODBC driver must already be installed on the target machine.
- Keep `config.json` next to the exe so paths and connection settings can be edited without rebuilding.
