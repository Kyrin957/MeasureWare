# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Resin MeasureWare (树脂测量软件).

Build command:
    .venv/Scripts/pyinstaller ResinMeasureWare.spec

Output will be in dist/ResinMeasureWare/
"""

import sys
from pathlib import Path

# ---- Paths ----
ROOT = Path(SPECPATH)  # directory containing this .spec file

# ---- Analyze the main entry script ----
a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Application icon
        (str(ROOT / "assets" / "favicon.ico"), "assets"),
        # Qt stylesheet
        (str(ROOT / "resources" / "style.qss"), "resources"),
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtCharts",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        # SQLAlchemy dialects
        "sqlalchemy.sql.default_comparator",
        "sqlalchemy.ext.declarative",
        # pandas (sub-modules frequently missed)
        "pandas._libs",
        "pandas._libs.tslibs",
        "pandas.io.sql",
        # Standard library modules sometimes missed
        "sqlite3",
        "logging",
        "json",
        "csv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unused Qt modules to reduce size
        "PySide6.QtBluetooth",
        "PySide6.QtDBus",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtLocation",
        "PySide6.QtMultimedia",
        "PySide6.QtNfc",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtXml",
        "PySide6.QtXmlPatterns",
        # Unused large stdlib modules
        "tkinter",
        "turtle",
        "unittest",
        "test",
        "pydoc",
        "distutils",
        "setuptools",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ---- Single-file executable ----
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ResinMeasureWare",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI app — no console window
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "favicon.ico"),
)

# ---- Optional: also produce a one-folder build for debugging ----
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name="ResinMeasureWare",
# )
