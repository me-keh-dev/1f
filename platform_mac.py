"""macOS固有のプラットフォーム実装"""
import threading
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QCursor

# --- DPI ---
def init_dpi():
    pass  # macOSはQt側で自動処理

# --- アプリ初期化（QApplication作成後に呼ぶ）---
def setup_mac_app():
    """メニューバーアイコンを正しく表示するためにActivation Policyを設定する。
    QApplication作成後、tray.show()より前に呼ぶこと。"""
    try:
        from AppKit import NSApplication
        # NSApplicationActivationPolicyAccessory = 1
        # Dockに表示せず、メニューバーアイコン(QSystemTrayIcon)が正しく機能する
        NSApplication.sharedApplication().setActivationPolicy_(1)
    except Exception:
        pass

# --- クリック透過 ---
def set_click_through(hwnd):
    """オーバーレイウィンドウのみを対象に設定する（全ウィンドウには適用しない）。
    - クリック透過 (setIgnoresMouseEvents_)
    - 全Spaceで表示 (NSWindowCollectionBehaviorCanJoinAllSpaces)
    - 最前面固定 (NSFloatingWindowLevel)
    """
    try:
        import objc
        from AppKit import NSFloatingWindowLevel
        # NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
        NSWindowCollectionBehaviorCanJoinAllSpaces = 1

        # hwnd は PyQt5 が返す NSView* ポインタ
        ns_view = objc.objc_object(c_void_p=int(hwnd))
        ns_window = ns_view.window()
        if ns_window is not None:
            ns_window.setLevel_(NSFloatingWindowLevel)
            ns_window.setIgnoresMouseEvents_(True)
            # CanJoinAllSpaces(1) | Stationary(16) — 全Space表示、Exposéで動かない
            ns_window.setCollectionBehavior_(1 | 16)
            # NSPanel はデフォルト hidesOnDeactivate=True のため、
            # ダイアログ表示時などにアプリが非アクティブになると隠れてしまう
            try:
                ns_window.setHidesOnDeactivate_(False)
            except Exception:
                pass
    except Exception:
        pass

def ensure_topmost(hwnd):
    """macOSではset_click_throughで設定済みのため追加処理不要"""
    pass

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

# --- スタートアップ ---
import os
import sys
import plistlib

def _launch_agent_path():
    return os.path.expanduser("~/Library/LaunchAgents/com.1f-yuragi.plist")

def _get_exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])

def is_startup_enabled():
    return os.path.exists(_launch_agent_path())

def set_startup_enabled(enabled):
    plist_path = _launch_agent_path()
    if enabled:
        target = _get_exe_path()
        plist = {
            "Label": "com.1f-yuragi",
            "ProgramArguments": [target],
            "RunAtLoad": True,
            "WorkingDirectory": os.path.dirname(target),
        }
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
    else:
        if os.path.exists(plist_path):
            os.remove(plist_path)
