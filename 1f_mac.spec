# -*- mode: python ; coding: utf-8 -*-
# macOS build spec for 1/f
#
# Usage (run on macOS):
#   pip install -r requirements.txt pyinstaller
#   pyinstaller 1f_mac.spec
#
# Output: dist/1f.app


# App code ships as plain .py data files (swappable without rebuilding);
# only bootstrap.py + dependencies (Python, PyQt5, pyobjc, stdlib) are frozen.
import os as _os
APP_CODE = [
    ('main.py', '.'), ('i18n.py', '.'), ('weather.py', '.'),
    ('weather_fx.py', '.'), ('platform_mac.py', '.'), ('audio_level.py', '.'),
    ('version.py', '.'), ('updater.py', '.'), ('stats.py', '.'),
    ('scenes', 'scenes'),
]
# 非公開モード（別リポジトリ管理）。存在する場合のみ .py だけ同梱する
# （ディレクトリ丸ごとだと .git までバンドルされるため列挙する）
if _os.path.isdir('private_scenes'):
    for _root, _dirs, _files in _os.walk('private_scenes'):
        _dirs[:] = [d for d in _dirs
                    if d != '__pycache__' and not d.startswith('.')]
        for _f in _files:
            if _f.endswith('.py'):
                _p = _os.path.join(_root, _f)
                APP_CODE.append((_p, _os.path.dirname(_p)))

a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.')] + APP_CODE,
    # pyobjc is used by the swappable platform_mac.py, so freeze it explicitly
    hiddenimports=['objc', 'AppKit', 'Quartz', 'plistlib'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['main', 'i18n', 'weather', 'weather_fx', 'platform_win', 'platform_mac', 'audio_level', 'version', 'updater', 'stats', 'scenes', 'private_scenes'],
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
