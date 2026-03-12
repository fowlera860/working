# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for CyclePlanner UpdateCyclePlanner.py

block_cipher = None

a = Analysis(
    ['UpdateCyclePlanner.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Don't bundle config.json - let users keep it next to the exe
    ],
    hiddenimports=[
        'mill_order_production_assignment_converter',
        'mill_order_roll_assignment_converter',
        'unassigned_mill_orders_converter',
        'inventory_converter',
        'product_specs_converter',
        'yarnxref_converter',
        'sales_forecast_converter',
        'mill_orders_converter',
        'production_orders_converter',
        'time_phase_production_orders_converter',
        'time_phase_shipments_converter',
        'cycle_planner_prebuild_converter',
        'cycle_planner_yarn_demand_converter',
        'utils',
        'numpy',
        'pandas',
        'pyodbc',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython',
        'matplotlib',
        'numba',
        'numexpr',
        'pyarrow',
        'pytest',
        'scipy',
        'tables',
        'sqlalchemy',
        'lxml',
        'bs4',
        'xlsxwriter',
        'xlrd',
        'pyxlsb',
        'python_calamine',
        'odf',
        'fsspec',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='UpdateCyclePlanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console window enabled
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add an .ico file path here if you want a custom icon
)
