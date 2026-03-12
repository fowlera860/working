# Building an EXE with PyInstaller

## Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

Recommended on a new PC: build from a clean virtual environment (Python 3.11/3.12).

## Build the EXE

### Option 1: Using the spec file (recommended)
```bash
pyinstaller --clean --noconfirm UpdateCyclePlanner.spec
```

This spec is configured with `console=True`, so the EXE runs with a console window.

### Option 2: Command line (simpler, but less control)
```bash
pyinstaller --onefile --windowed --add-data "config.json;." UpdateCyclePlanner.py
```

## Output

The executable will be created in the `dist/` folder:
- `dist/UpdateCyclePlanner.exe`

## Running the EXE

Simply run the executable from any location:
```bash
UpdateCyclePlanner.exe
```

If you run from Command Prompt and want it to close immediately at the end, use:
```bash
UpdateCyclePlanner.exe --no-pause
```

**Important:** The `config.json` file is bundled into the exe, but the Excel files and export paths in the config still need to be accessible from your network locations.

## Troubleshooting

### Huge "missing module" list from PyInstaller
`build/.../warn-*.txt` is often noisy and includes optional imports from `pandas`/`numpy` and OS-specific modules.

Examples that are usually safe to ignore when building on Windows:
- `pwd`, `grp`, `posix`, `_posixsubprocess`, `fcntl` (Unix-only modules)
- optional pandas extras (`pyarrow`, `numba`, `scipy`, `matplotlib`, `sqlalchemy`, etc.)

Treat this as a real issue only if one of your app's required modules is missing at runtime.

### Build from a clean venv (recommended)
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install pandas numpy pyodbc openpyxl pyinstaller
pyinstaller --clean --noconfirm UpdateCyclePlanner.spec
```

### If build still fails on a new machine
1. Confirm Python and PyInstaller versions:
	```bash
	python --version
	pyinstaller --version
	```
2. Prefer Python 3.11 or 3.12 for packaging stability.
3. Delete `build/` and `dist/` folders, then rebuild with `--clean`.
4. Check antivirus/endpoint protection is not quarantining temporary PyInstaller files.
5. Verify you are launching the newly-built file from `dist/` (not an older copy elsewhere).

### "Module not found" errors
Add missing modules to `hiddenimports` in the spec file.

### "Config.json not found"
Make sure `config.json` is in the same folder as `UpdateCyclePlanner.py` when building.

### ODBC Driver errors
The exe doesn't include the ODBC Driver - it must be installed on the target machine:
- Download: Microsoft ODBC Driver 17 or 18 for SQL Server

### Large file size
The exe bundles Python, pandas, numpy, and all dependencies (~100-200 MB is normal).

## Distribution

To share the executable:
1. Copy `dist/UpdateCyclePlanner.exe` to the target machine
2. Ensure ODBC Driver 17+ for SQL Server is installed
3. Ensure network paths in the bundled config.json are accessible
4. Run the exe - no Python installation needed!

## Rebuilding

If you make changes to any converter files:
1. Update the code
2. Run `pyinstaller --clean --noconfirm UpdateCyclePlanner.spec` again
3. New exe will be in `dist/` folder
