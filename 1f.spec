# -*- mode: python ; coding: utf-8 -*-


# App code ships as plain .py data files (swappable without rebuilding);
# only bootstrap.py + dependencies (Python, PyQt5, stdlib) are frozen.
import os as _os
APP_CODE = [
    ('main.py', '.'), ('i18n.py', '.'), ('weather.py', '.'),
    ('weather_fx.py', '.'), ('platform_win.py', '.'), ('audio_level.py', '.'),
    ('version.py', '.'), ('updater.py', '.'), ('stats.py', '.'),
    ('scenes', 'scenes'),
]
# 非公開モード（別リポジトリ管理）。存在する場合のみ直下の .py だけ同梱する
# （丸ごとだと .git や creator_kit 等の未公開資料までバンドルされるため）
if _os.path.isdir('private_scenes'):
    for _f in _os.listdir('private_scenes'):
        if _f.endswith('.py'):
            APP_CODE.append((_os.path.join('private_scenes', _f),
                             'private_scenes'))

a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.')] + APP_CODE,
    hiddenimports=['soundcard', 'numpy'],  # サウンド連動（audio_level.py が使用）
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
