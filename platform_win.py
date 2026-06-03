"""Windows固有のプラットフォーム実装"""
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

def set_click_through(hwnd):
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE,
        style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
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
