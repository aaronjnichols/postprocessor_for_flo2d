# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for FLO-2D Postprocessor GUI.

This spec file creates a single-file Windows executable with all dependencies.

Build command:
    pyinstaller flo2d_postprocessor.spec

For development builds (faster, larger):
    pyinstaller flo2d_postprocessor.spec --onedir

Requirements:
    pip install pyinstaller
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path(SPECPATH)

# Application metadata
APP_NAME = 'FLO2D_Postprocessor'
APP_VERSION = '1.0.0'

# Analysis configuration
a = Analysis(
    ['gui/launch_gui.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include any data files needed by the application
        ('config.example.json', '.'),
    ],
    hiddenimports=[
        # GeoPandas and related
        'geopandas',
        'fiona',
        'fiona.crs',
        'fiona._shim',
        'fiona.schema',
        'pyproj',
        'pyproj.crs',
        'pyproj._crs',
        'pyproj._transformer',
        'pyproj.database',
        'shapely',
        'shapely.geometry',
        'shapely.ops',
        'shapely._geometry_helpers',

        # Rasterio
        'rasterio',
        'rasterio._shim',
        'rasterio.crs',
        'rasterio.sample',
        'rasterio.vrt',
        'rasterio.features',
        'rasterio._base',

        # Pandas and NumPy
        'pandas',
        'pandas._libs.hashtable',
        'pandas._libs.tslibs.timedeltas',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',

        # Dask
        'dask',
        'dask.dataframe',
        'dask_geopandas',

        # Excel support
        'openpyxl',
        'xlsxwriter',

        # Matplotlib
        'matplotlib',
        'matplotlib.backends.backend_tkagg',

        # Tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'ttkthemes',

        # Application modules
        'core',
        'core.constants',
        'core.file_discovery',
        'core.model_data_extraction',
        'core.utilities',
        'core.auto_updater',
        'extraction',
        'extraction.dat',
        'extraction.out',
        'processing',
        'processing.spatial',
        'processing.vectorization',
        'processing.output',
        'reporting',
        'reporting.spreadsheets',
        'reporting.visualization',
        'gui',
        'gui.flo2d_postprocessor_gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'docutils',
    ],
    noarchive=False,
    optimize=0,
)

# Create the PYZ archive
pyz = PYZ(a.pure)

# Single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available: 'assets/icon.ico'
    version=None,  # Add version info file if available
)

# Alternatively, for a directory-based distribution (faster startup):
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name=APP_NAME,
# )
