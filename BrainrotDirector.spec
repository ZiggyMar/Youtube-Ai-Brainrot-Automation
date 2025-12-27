# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['F:\\!Deeo\\AI Project\\Youtube-Ai-Brainrot-Automation\\gui\\main_window.py'],
    pathex=[],
    binaries=[],
    datas=[('F:\\!Deeo\\AI Project\\Youtube-Ai-Brainrot-Automation\\core', 'core'), ('F:\\!Deeo\\AI Project\\Youtube-Ai-Brainrot-Automation\\gui', 'gui'), ('F:\\!Deeo\\AI Project\\Youtube-Ai-Brainrot-Automation\\data', 'data')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='BrainrotDirector',
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
