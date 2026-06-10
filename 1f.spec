# -*- mode: python ; coding: utf-8 -*-


# App code ships as plain .py data files (swappable without rebuilding);
# only bootstrap.py + dependencies (Python, PyQt5, stdlib) are frozen.
APP_CODE = [
    ('main.py', '.'), ('i18n.py', '.'), ('weather.py', '.'),
    ('weather_fx.py', '.'), ('platform_win.py', '.'), ('scenes', 'scenes'),
]

a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.')] + APP_CODE,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['main', 'i18n', 'weather', 'weather_fx', 'platform_win', 'platform_mac', 'scenes'],
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
    name='1f',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir='.',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
