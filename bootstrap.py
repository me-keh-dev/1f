"""1/f bootstrap: the frozen "skeleton" entry point.

The PyInstaller binary freezes only this file plus the heavy dependencies
(Python runtime, PyQt5, stdlib). The application code itself (main.py,
scenes/, i18n.py, ...) is shipped as plain .py data files and loaded via
sys.path, so it can be updated by swapping files - no rebuild needed.

Search order for application code:
  1. External code dir (survives app updates, used for hot-swap updates):
       Windows: %APPDATA%/1f/code
       macOS:   ~/Library/Application Support/1f/code
  2. The bundled copy inside the app (fallback / first run)

To update the app without rebuilding: put the new .py files (same layout
as the repository: main.py, i18n.py, weather.py, weather_fx.py,
platform_win.py / platform_mac.py, scenes/) into the external code dir.
To go back to the bundled version, delete the external code dir.
"""

# --- Skeleton dependencies -------------------------------------------------
# Static imports so PyInstaller bundles everything the swappable app code
# may need. Keep this list in sync with the imports used across the app.
import sys
import os
import json
import math
import random
import time
import datetime
import threading
import locale
import urllib.request
import urllib.error
import ctypes  # noqa: F401  (platform_win)
from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: F401

if sys.platform == "win32":
    from ctypes import wintypes  # noqa: F401


# スケルトン（凍結部）の版数。PyQt等の依存やbootstrap自体が変わったら上げる。
# 上がると updater がコア更新（インストーラーDL）を案内する
SKELETON_VERSION = 1


def external_code_dir():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/1f")
    else:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "1f")
    return os.path.join(base, "code")


def bundled_code_dir():
    # onefile: extraction dir / onedir: the app's internal dir
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def run():
    # 差し替え可能なコード側（updater）へスケルトン版数を伝える
    os.environ["ONEF_SKELETON_VERSION"] = str(SKELETON_VERSION)
    sys.path.insert(0, bundled_code_dir())
    ext = external_code_dir()
    if os.path.isfile(os.path.join(ext, "main.py")):
        sys.path.insert(0, ext)  # external code wins over the bundled copy
    import main
    main.main()


if __name__ == "__main__":
    run()
