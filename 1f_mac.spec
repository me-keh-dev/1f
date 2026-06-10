# -*- mode: python ; coding: utf-8 -*-
# macOS build spec for 1/f
#
# Usage (run on macOS):
#   pip install -r requirements.txt pyinstaller
#   pyinstaller 1f_mac.spec
#
# Output: dist/1f.app


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.'), ('i18n.py', '.'), ('weather.py', '.'), ('weather_fx.py', '.'), ('scenes', 'scenes')],
    hiddenimports=[
        'scenes', 'scenes.base', 'scenes.grass', 'scenes.aquarium',
        'scenes.tokaido', 'scenes.pooh', 'scenes.takibi',
        # platform_mac is imported conditionally (sys.platform), so list it
        # and its pyobjc dependencies explicitly
        'platform_mac', 'objc', 'AppKit', 'Quartz',
    ],
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
    [],
    exclude_binaries=True,
    name='1f',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='1f',
)
app = BUNDLE(
    coll,
    name='1f.app',
    icon='icon.icns',
    bundle_identifier='com.1f',
    info_plist={
        'NSHighResolutionCapable': True,
        # Menu-bar (tray) app: no Dock icon
        'LSUIElement': True,
        'CFBundleShortVersionString': '2.3.0',
    },
)
