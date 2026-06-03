"""macOS固有のプラットフォーム実装"""
import subprocess
import threading
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QCursor

# --- DPI ---
def init_dpi():
    pass  # macOSはQt側で自動処理

# --- クリック透過 ---
def set_click_through(hwnd):
    # macOSではQt.WA_TransparentForMouseEventsで十分
    # NSWindowレベルでの追加設定が必要な場合はpyobjcを使用
    try:
        import objc
        from AppKit import NSApplication, NSFloatingWindowLevel
        app = NSApplication.sharedApplication()
        for window in app.windows():
            window.setLevel_(NSFloatingWindowLevel)
            window.setIgnoresMouseEvents_(True)
    except ImportError:
        pass  # pyobjcがない場合はQtのフォールバックに頼る

# --- カーソル位置 ---
def get_cursor_pos():
    pos = QCursor.pos()
    return pos.x(), pos.y()

# --- グローバルホットキー ---
class HotkeySignal(QObject):
    triggered = pyqtSignal()

class HotkeyListener:
    """macOS用ホットキー監視 (Cmd+Ctrl+Shift+W)"""
    def __init__(self, callback):
        self.signal = HotkeySignal()
        self.signal.triggered.connect(callback)
        self._running = True
        self._thread = None
        self._setup_hotkey()

    def _setup_hotkey(self):
        try:
            import objc
            from Cocoa import NSEvent, NSKeyDownMask
            from Cocoa import NSCommandKeyMask, NSControlKeyMask, NSShiftKeyMask

            mask = NSCommandKeyMask | NSControlKeyMask | NSShiftKeyMask

            def handler(event):
                if event.keyCode() == 13:  # W key
                    self.signal.triggered.emit()

            NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                NSKeyDownMask, handler
            )
        except ImportError:
            # pyobjcがない場合はQTimerでキーポーリング（フォールバック）
            self._timer = QTimer()
            self._timer.timeout.connect(self._poll_keys)
            self._timer.start(100)

    def _poll_keys(self):
        pass  # フォールバック: トレイメニューからの操作に頼る

    def cleanup(self):
        self._running = False
