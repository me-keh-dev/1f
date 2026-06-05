"""Windows固有のプラットフォーム実装"""
import os
import sys
import ctypes
from ctypes import wintypes
import threading
from PyQt5.QtCore import pyqtSignal, QObject

# --- DPI ---
def init_dpi():
    ctypes.windll.user32.SetProcessDPIAware()

# --- クリック透過 ---
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

def set_click_through(hwnd):
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE,
        style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
    )
    # Win32 APIで確実にTOPMOSTに設定
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )

def ensure_topmost(hwnd):
    """定期的に呼んで最前面を再設定する"""
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )

# --- カーソル位置 ---
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

# --- グローバルホットキー ---
MOD_WIN = 0x0008
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
VK_W = 0x57
HOTKEY_TOGGLE = 1
WM_HOTKEY = 0x0312

class HotkeySignal(QObject):
    triggered = pyqtSignal()

class HotkeyListener:
    """別スレッドでWin32メッセージループを回してホットキーを監視"""
    def __init__(self, callback):
        self.signal = HotkeySignal()
        self.signal.triggered.connect(callback)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        result = ctypes.windll.user32.RegisterHotKey(
            None, HOTKEY_TOGGLE,
            MOD_WIN | MOD_CTRL | MOD_SHIFT, VK_W
        )
        if not result:
            return
        msg = wintypes.MSG()
        while self._running:
            ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_TOGGLE:
                self.signal.triggered.emit()
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_TOGGLE)

    def cleanup(self):
        self._running = False
        tid = self._thread.ident
        if tid:
            ctypes.windll.user32.PostThreadMessageW(tid, 0x0000, 0, 0)

# --- 全画面検出 ---
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]

def is_fullscreen_active():
    """前面ウィンドウがモニター全体を覆っているか（全画面状態）を判定"""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return False
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    MONITOR_DEFAULTTONEAREST = 2
    hmon = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    mon = mi.rcMonitor
    return (rect.left <= mon.left and rect.top <= mon.top and
            rect.right >= mon.right and rect.bottom >= mon.bottom)

# --- スタートアップ ---
def _startup_shortcut_path():
    startup = os.path.join(os.environ["APPDATA"],
                           "Microsoft", "Windows", "Start Menu",
                           "Programs", "Startup", "1f Yuragi.lnk")
    return startup

def _get_exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])

def is_startup_enabled():
    return os.path.exists(_startup_shortcut_path())

def set_startup_enabled(enabled):
    shortcut_path = _startup_shortcut_path()
    if enabled:
        target = _get_exe_path()
        working_dir = os.path.dirname(os.path.abspath(target))
        # exe以外（python main.py）の場合はpythonw経由で起動するショートカットを作る
        if not getattr(sys, 'frozen', False):
            python_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable
            args = f'"{python_exe}" "{os.path.abspath(target)}"'
            sc_target = python_exe
            sc_args = f'"{os.path.abspath(target)}"'
        else:
            sc_target = target
            sc_args = ""
        try:
            vbs = os.path.join(os.environ["TEMP"], "create_shortcut.vbs")
            with open(vbs, "w") as f:
                f.write(f'Set ws = CreateObject("WScript.Shell")\n')
                f.write(f'Set sc = ws.CreateShortcut("{shortcut_path}")\n')
                f.write(f'sc.TargetPath = "{sc_target}"\n')
                if sc_args:
                    f.write(f'sc.Arguments = {sc_args}\n')
                f.write(f'sc.WorkingDirectory = "{working_dir}"\n')
                f.write(f'sc.Save\n')
            os.system(f'cscript //nologo "{vbs}"')
            if os.path.exists(vbs):
                os.remove(vbs)
        except Exception as e:
            print(f"[WARN] Failed to create startup shortcut: {e}")
    else:
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
