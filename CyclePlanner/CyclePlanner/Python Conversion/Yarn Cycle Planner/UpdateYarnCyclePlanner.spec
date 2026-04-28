# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Yarn Cycle Planner UpdateYarnCyclePlanner.py

block_cipher = None

a = Analysis(
    ['UpdateYarnCyclePlanner.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Don't bundle config.json - let users keep it next to the exe
    ],
    hiddenimports=[
        'FIN_yarn_inventory_converter',
        'WIP_yarn_inventory_converter',
        'yarn_cycle_planner_prebuild_converter',
        'pending_yarn_orders_converter',
        'yarn_assignments_converter',
        'yarn_lot_aggregate_converter',
        'open_yarn_production_converter',
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
    name='UpdateYarnCyclePlanner',
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
