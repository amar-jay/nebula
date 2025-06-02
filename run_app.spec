# -*- mode: python ; coding: utf-8 -*-
# Add this at the top
from PyInstaller.utils.hooks import collect_data_files

# Collect MAVLink dialects
datas = collect_data_files("pymavlink", includes=[
"venv/lib/python3.10/site-packages/pymavlink/dialects/v20/*.xml",
#"venv/lib/python3.10/site-packages/pymavlink/dialects/v10/*.xml",
#"venv/lib/python3.10/site-packages/pymavlink/dialects/v1.0/*.xml",
])

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=datas + [],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PyQt6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='run_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
