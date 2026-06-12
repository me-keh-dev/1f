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
