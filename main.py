"""
1/f - ADHDの集中支援デスクトップオーバーレイ
タスクバーの上にプロシージャル生成のドット絵草を表示し、1/fゆらぎで揺らす
風が左から右に波のように伝播し、高原の草原のようになびく
"""
import sys
import os
import json
import math
import random
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QAction,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGroupBox, QComboBox,
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QIcon, QPixmap, QFont, QPainterPath

# プラットフォーム固有モジュールの読み込み
if sys.platform == "win32":
    from platform_win import init_dpi, set_click_through, set_clickable, is_shift_pressed, ensure_topmost, set_behind_windows, get_cursor_pos, HotkeyListener, is_startup_enabled, set_startup_enabled, is_fullscreen_active
elif sys.platform == "darwin":
    from platform_mac import init_dpi, setup_mac_app, set_click_through, set_clickable, is_shift_pressed, ensure_topmost, set_behind_windows, is_fullscreen_active, get_cursor_pos, HotkeyListener, is_startup_enabled, set_startup_enabled
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

init_dpi()

from i18n import t, set_language, get_language, detect_language
from weather import WeatherMonitor
from audio_level import AudioLevelMonitor, is_supported as audio_supported
from weather_fx import WeatherEffect, WIND_SPEED_CALM, WIND_SPEED_MAX
import scenes as scenes_registry
from scenes import (
    get_scene_class, get_scene_info, get_scale_key, get_preset_keys,
    scene_registry, scene_modes, limited_until, SCENE_MODES,
)


def _scene_label(mode_key, label_key):
    """モード名ラベル。期間限定モードは終了日を添える（例: 〜7/31）"""
    label = t(label_key)
    until = limited_until(mode_key)
    if until:
        if get_language() == "ja":
            label += "（〜{}/{}）".format(until.month, until.day)
        else:
            label += " (until {}/{})".format(until.month, until.day)
    return label
from scenes.base import PinkNoiseGenerator, PIXEL_SIZE, HAMBURGER_BASE
import updater
import stats

def _app_dir():
    """設定・セーブの保存先。
    Windows exe: exeのあるフォルダ（ポータブル運用）
    mac .app: ~/Library/Application Support/1f
      （.appバンドル内は App Translocation で読み取り専用＆毎回パスが変わるため）
    スクリプト実行: スクリプトのフォルダ"""
    if getattr(sys, 'frozen', False):
        if sys.platform == "darwin":
            d = os.path.expanduser("~/Library/Application Support/1f")
            os.makedirs(d, exist_ok=True)
            return d
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _resource_dir():
    """バンドル内リソース（読み取り専用）のディレクトリ"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _log_dir():
    """クラッシュログの保存先（%APPDATA%/1f ほか、updaterの外部コードと同じ場所）"""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/1f")
    else:
        base = os.path.join(os.environ.get("APPDATA", _app_dir()), "1f")
    os.makedirs(base, exist_ok=True)
    return base


def _setup_crash_logging():
    """安定性対策。
    - PyQt5.5以降はスロット内の未捕捉Python例外で qFatal → 即クラッシュする。
      excepthook を入れてログに記録し、アプリは落とさず続行する。
    - ネイティブクラッシュ（Cレベル）は faulthandler でスタックをファイルに残す。
    """
    import faulthandler
    import traceback
    import threading as _th
    import datetime as _dt
    try:
        from version import CODE_VERSION as _ver
    except Exception:
        _ver = "?"
    log_path = os.path.join(_log_dir(), "error.log")
    fault_path = os.path.join(_log_dir(), "crash.log")
    try:
        # 古いログの肥大化防止
        if os.path.isfile(log_path) and os.path.getsize(log_path) > 512 * 1024:
            os.remove(log_path)
        # faulthandler用ファイルは開きっぱなしにする必要がある
        _setup_crash_logging._fh = open(fault_path, "a", encoding="utf-8")
        faulthandler.enable(file=_setup_crash_logging._fh)
    except Exception:
        pass

    def _log_exc(prefix, exc_type, exc, tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n[{} v{} {}]\n".format(
                    _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    _ver, prefix))
                traceback.print_exception(exc_type, exc, tb, file=f)
        except Exception:
            pass

    def _hook(exc_type, exc, tb):
        _log_exc("uncaught", exc_type, exc, tb)
        # 落とさず続行（KeyboardInterruptのみ既定動作）
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    def _thread_hook(args):
        _log_exc("thread:" + (args.thread.name if args.thread else "?"),
                 args.exc_type, args.exc_value, args.exc_traceback)

    _th.excepthook = _thread_hook


def _collect_error_logs():
    """前回までに記録されたエラーログを読み、匿名化して返す（なければ None）。
    crash.log は起動時に faulthandler が開くため、今読める内容＝前回以前の分。
    """
    parts = []
    for name in ("error.log", "crash.log"):
        path = os.path.join(_log_dir(), name)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            if text:
                parts.append("===== {} =====\n{}".format(name, text))
        except OSError:
            pass
    if not parts:
        return None
    log = "\n\n".join(parts)[-60000:]
    # 匿名化: パス中のホームディレクトリ（ユーザー名）を伏せる
    home = os.path.expanduser("~")
    log = log.replace(home, "~").replace(home.replace("\\", "/"), "~")
    return log


def _clear_error_logs():
    """報告（または辞退）済みのログを空にする。次回は新しいエラーだけ対象になる"""
    for name in ("error.log", "crash.log"):
        try:
            # faulthandler が開いたままでも Windows で truncate できるよう r+ で
            with open(os.path.join(_log_dir(), name), "r+", encoding="utf-8") as f:
                f.truncate(0)
        except OSError:
            pass


def _maybe_offer_error_report(config):
    """前回エラーが記録されていたら、同意の上で匿名送信する（起動数秒後に呼ぶ）"""
    log = _collect_error_logs()
    if not log:
        return
    from PyQt5.QtWidgets import QMessageBox
    ret = QMessageBox.question(
        None, t("errlog_title"), t("errlog_ask"),
        QMessageBox.Yes | QMessageBox.No)
    if ret == QMessageBox.Yes:
        try:
            from version import CODE_VERSION as ver
        except Exception:
            ver = "?"
        import platform as _pf
        stats.submit_errlog({
            "ver": ver,
            "skeleton": os.environ.get("ONEF_SKELETON_VERSION", "0"),
            "platform": sys.platform,
            "os": _pf.platform(),
            "log": log,
        }, base_url=config.get("stats_url"))
    # 送信・辞退どちらでも消す（同じログで何度も聞かない）
    _clear_error_logs()

APP_DIR = _app_dir()
SAVE_DIR = os.path.join(APP_DIR, "saves")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")







# --- 時間帯ライティング ---
import datetime

# 時間帯ごとの色調 (r_mult, g_mult, b_mult) — 1.0が元の色
TIME_LIGHTING = [
    # (hour, r, g, b)
    (0,   0.25, 0.28, 0.55),  # 深夜: 青い月明かり
    (4,   0.30, 0.30, 0.55),  # 未明: 暗い青
    (5,   0.55, 0.40, 0.50),  # 薄明: 紫がかった暗さ
    (6,   0.90, 0.60, 0.50),  # 朝焼け: オレンジピンク
    (7,   1.00, 0.85, 0.70),  # 早朝: 暖かい光
    (8,   1.00, 0.95, 0.90),  # 朝: ほぼ自然光
    (10,  1.00, 1.00, 1.00),  # 日中: そのまま
    (16,  1.00, 1.00, 0.95),  # 午後: わずかに暖色
    (17,  1.00, 0.90, 0.70),  # 夕方: 暖かい光
    (18,  1.00, 0.65, 0.45),  # 夕暮れ: オレンジ
    (19,  0.80, 0.50, 0.45),  # 日没: 赤みがかる
    (20,  0.45, 0.38, 0.55),  # 薄暮: 紫
    (21,  0.30, 0.32, 0.55),  # 夜: 青い月明かり
    (24,  0.25, 0.28, 0.55),  # 深夜（ループ）
]

def _get_time_tint():
    """現在時刻に基づいて色の掛け算値 (r, g, b) を返す"""
    now = datetime.datetime.now()
    hour = now.hour + now.minute / 60.0

    # 補間
    for i in range(len(TIME_LIGHTING) - 1):
        h1, r1, g1, b1 = TIME_LIGHTING[i]
        h2, r2, g2, b2 = TIME_LIGHTING[i + 1]
        if h1 <= hour < h2:
            t = (hour - h1) / (h2 - h1)
            return (
                r1 + (r2 - r1) * t,
                g1 + (g2 - g1) * t,
                b1 + (b2 - b1) * t,
            )
    return (1.0, 1.0, 1.0)

# 手動で選べる固定プリセット
LIGHTING_PRESETS = {
    "sunrise": (0.90, 0.60, 0.50),   # 朝焼け
    "daytime": (1.00, 1.00, 1.00),   # 日中
    "sunset":  (1.00, 0.65, 0.45),   # 夕暮れ
    "night":   (0.30, 0.32, 0.55),   # 夜（月明かり）
}





class WindSimulator:
    def __init__(self):
        self.time = 0.0
        self.base_strength = 1.0
        self.wave_speed = 300.0
        self.wave_length = 400.0
        self.gust_noise = PinkNoiseGenerator()
        self.gust_timer = 0.0
        self.gust_value = 0.0
        self.current_gust = 0.0
        self.sound_level = 0.0  # サウンド連動 0..2（音量×感度）
        self.sound_bass = 0.0   # キックの「ドン!」パルス 0..2（焚火の爆ぜ・草の首振り）

    def set_wind(self, wind_value):
        ratio = wind_value / 50.0
        self.base_strength = ratio
        self.wave_speed = 150 + ratio * 250
        self.wave_length = 250 + ratio * 200

    def update(self, dt):
        self.time += dt
        # 突風の1/fゆらぎ: ゆっくり変化する強弱
        self.gust_timer += dt
        if self.gust_timer > 0.15:
            self.gust_timer = 0.0
            self.gust_value = self.gust_noise.next()
        # 突風サイクル: たまに強く吹く (数秒おきにピーク)
        gust_wave = math.sin(self.time * 0.4) * 0.3  # ゆっくり周期
        gust_wave += math.sin(self.time * 0.17) * 0.2  # さらにゆっくり
        self.current_gust = max(0, gust_wave + self.gust_value * 0.5)  # 0以上に

    def get_wave_at(self, x):
        phase = (x - self.wave_speed * self.time) / self.wave_length
        wave1 = math.sin(phase * 2 * math.pi)
        phase2 = (x - self.wave_speed * 1.3 * self.time) / (self.wave_length * 0.6)
        wave2 = math.sin(phase2 * 2 * math.pi) * 0.4
        phase3 = (x - self.wave_speed * 0.4 * self.time) / (self.wave_length * 2.5)
        wave3 = math.sin(phase3 * 2 * math.pi) * 0.3
        base = (wave1 + wave2 + wave3)
        # 突風とサウンド連動で振幅が増える（sound_bass はキックの瞬間だけ立つ
        # パルスなので、ドン!に合わせて首を振るような動きになる）
        strength = self.base_strength * (
            1.0 + self.current_gust * 1.5 + self.sound_level * 2.0 + self.sound_bass * 2.2)
        return base * strength


class NoWheelSlider(QSlider):
    """スクロール中に値が変わらないようホイールイベントを無視するスライダー"""
    def wheelEvent(self, event):
        event.ignore()

# --- 設定画面のスキン（QSSテーマ） ---
def _make_qss(c):
    """色セット c から設定ダイアログ用の QSS を生成する"""
    return """
    QDialog {{ background: {bg}; }}
    QLabel {{ color: {text}; background: transparent; }}
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px;
        background: {panel}; top: -1px; }}
    QTabBar::tab {{ background: {bg}; color: {text}; padding: 6px 12px;
        border-top-left-radius: 8px; border-top-right-radius: 8px;
        margin-right: 2px; }}
    QTabBar::tab:selected {{ background: {panel}; color: {text};
        border: 1px solid {border}; border-bottom: 2px solid {accent}; }}
    QTabBar::tab:hover {{ background: {panel}; }}
    QGroupBox {{ background: {panel}; border: 1px solid {border};
        border-radius: 8px; margin-top: 10px; padding-top: 10px;
        font-weight: 600; color: {text}; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
    QPushButton {{ background: {accent}; color: {on_accent}; border: none;
        border-radius: 6px; padding: 6px 12px; }}
    QPushButton:hover {{ background: {accent_hover}; }}
    QPushButton:pressed, QPushButton:checked {{ background: {accent_hover}; }}
    QComboBox {{ background: {field}; color: {text}; border: 1px solid {border};
        border-radius: 6px; padding: 3px 8px; }}
    QComboBox:hover {{ border-color: {accent}; }}
    QComboBox QAbstractItemView {{ background: {field}; color: {text};
        selection-background-color: {accent}; selection-color: {on_accent}; }}
    QCheckBox {{ color: {text}; spacing: 6px; background: transparent; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: {panel}; }}
    QSlider::groove:horizontal {{ height: 4px; background: {groove};
        border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {field}; border: 2px solid {accent};
        width: 14px; height: 14px; margin: -6px 0; border-radius: 9px; }}
    """.format(**c)


UI_SKINS = {
    "natural": _make_qss(dict(
        bg="#eef2ef", panel="#fbfcfb", field="#ffffff", text="#36413a",
        border="#dde3df", groove="#d8dfda", accent="#6bb758",
        accent_hover="#5aa648", on_accent="#ffffff")),
    "dark": _make_qss(dict(
        bg="#2b2f33", panel="#363b40", field="#3f464c", text="#e6ebe8",
        border="#474e54", groove="#4a5258", accent="#6bb758",
        accent_hover="#7cc869", on_accent="#10140f")),
    "sakura": _make_qss(dict(
        bg="#fbeef2", panel="#fffafc", field="#ffffff", text="#5a4750",
        border="#f0d9e1", groove="#f2dde4", accent="#e58aa6",
        accent_hover="#d97a98", on_accent="#ffffff")),
}
DEFAULT_SKIN = "natural"


# --- 設定ダイアログ ---
from PyQt5.QtWidgets import QTabWidget, QCheckBox, QScrollArea

class PollGraph(QWidget):
    """人気投票の横棒グラフ。数字は出さず、棒の長さだけで表す"""
    BAR_H = 20
    GAP = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []   # [(ラベル, 最大票に対する割合 0..1)]

    def set_counts(self, counts):
        labels = dict(SCENE_MODES)
        mx = max(counts.values(), default=0)
        rows = sorted(((k, n) for k, n in counts.items() if k in labels),
                      key=lambda kv: -kv[1])
        self.data = [(t(labels[k]), n / mx if mx else 0.0) for k, n in rows]
        voted = {k for k, _ in rows}
        for k, lk in SCENE_MODES:   # 票のないモードは末尾に空バー
            if k not in voted:
                self.data.append((t(lk), 0.0))
        self.setMinimumHeight(len(self.data) * (self.BAR_H + self.GAP))
        self.update()

    def clear(self):
        self.data = []
        self.setMinimumHeight(0)
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fm = p.fontMetrics()
        label_w = max(fm.boundingRect(lbl).width() for lbl, _ in self.data) + 14
        bar_max = max(10, self.width() - label_w - 10)
        y = 0
        for lbl, ratio in self.data:
            p.setPen(QColor(70, 70, 70))
            p.drawText(0, y, label_w - 8, self.BAR_H,
                       Qt.AlignRight | Qt.AlignVCenter, lbl)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(232, 232, 232))
            p.drawRoundedRect(label_w, y + 3, bar_max, self.BAR_H - 6, 4, 4)
            if ratio > 0:
                p.setBrush(QColor(110, 160, 210))
                p.drawRoundedRect(label_w, y + 3, max(int(bar_max * ratio), 10),
                                  self.BAR_H - 6, 4, 4)
            y += self.BAR_H + self.GAP
        p.end()


class SceneTile(QWidget):
    """iPhoneアプリアイコン風のシーンタイル。
    所有シーンはライブのミニプレビューを描き、マウスオンの間だけ動く。
    クリックで再生（所有）/ お試し（未購入）。"""
    THUMB_W = 128
    THUMB_H = 128   # 正方形

    HEART_R = 13   # ハートボタンの当たり半径

    def __init__(self, key, label, owned, price, url, on_play, on_trial,
                 favorited=False, on_favorite=None, parent=None):
        super().__init__(parent)
        self.key = key
        self.label = label
        self.owned = owned
        self.price = price
        self.url = url
        self.on_play = on_play
        self.on_trial = on_trial
        self.favorited = favorited
        self.on_favorite = on_favorite
        self._hover = False
        self.scene = None
        self._wind = WindSimulator()
        self.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.setCursor(Qt.PointingHandCursor)
        # ツールチップは出さない（ホバー中の動きを隠さないため）
        if owned:
            self._build_scene()
        elif url:
            self._build_preview()   # 未購入もプレビュー描画（中身は所有しない）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _heart_center(self):
        return self.THUMB_W - 20, self.THUMB_H - 20  # 右下（メルカリ風）

    def _build_scene(self):
        try:
            self._spin_up(get_scene_class(self.key)())
        except Exception:
            self.scene = None

    def _build_preview(self):
        """未購入シーンのプレビュー: カタログ署名パッケージを取得・検証して
        グローバル登録せずにクラスだけ得て描く（所有はしない）。失敗時は錠前表示。"""
        try:
            from scenes import _collab, load_scene_from_source
            _key, src = _collab.fetch_trial(self.url)
            info = load_scene_from_source(src, self.key)
            if info and info.get("class"):
                self._preview_scale_key = info.get("scale_key", "")
                self._spin_up(info["class"]())
        except Exception:
            self.scene = None

    def _spin_up(self, scene):
        cfg = {"seed": 7, get_scale_key(self.key): 70,
               getattr(self, "_preview_scale_key", "_") or "_": 70}
        self.scene = scene
        self.scene.rebuild(cfg, self.THUMB_W, self.THUMB_W)
        self._wind.set_wind(80)   # プレビューは少し強めの風で動きを見せる
        for _ in range(15):
            self._wind.update(1 / 60.0)
            self.scene.update(self._wind)

    def enterEvent(self, event):
        self._hover = True
        if self.scene:
            self._timer.start(33)   # ホバー中だけ ~30fps で動かす
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self._timer.stop()
        self.update()

    def _tick(self):
        if self.scene:
            # 通常より速い時間進行でプレビューの動きをはっきり見せる
            self._wind.update(1 / 14.0)
            try:
                self.scene.update(self._wind)
            except Exception:
                self._timer.stop()
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        # ハート（お気に入り）の当たり判定が最優先
        hx, hy = self._heart_center()
        if (event.pos().x() - hx) ** 2 + (event.pos().y() - hy) ** 2 \
                <= self.HEART_R ** 2:
            self.favorited = not self.favorited
            if self.on_favorite:
                self.on_favorite(self.key, self.favorited)
            self.update()
            return
        if self.owned:
            self.on_play(self.key)
        else:
            self.on_trial(self.key, self.url)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        tw, th = self.THUMB_W, self.THUMB_H
        # サムネ枠（角丸クリップ）
        path = QPainterPath()
        path.addRoundedRect(0, 0, tw, th, 10, 10)
        p.setClipPath(path)
        p.fillRect(0, 0, tw, th, QColor(150, 175, 200))  # 空
        if self.scene:
            p.setRenderHint(QPainter.Antialiasing, False)
            try:
                if self.scene.has_background_layer():
                    self.scene.draw_background(p, th, None, None)
                self.scene.draw(p, th, None, None)
            except Exception:
                pass
            p.setRenderHint(QPainter.Antialiasing, True)
        else:
            # 未購入: 中身が無いので錠前風プレースホルダ
            p.fillRect(0, 0, tw, th, QColor(70, 78, 92))
            p.setPen(QColor(210, 215, 225))
            f = p.font(); f.setPointSize(20); p.setFont(f)
            p.drawText(0, 0, tw, th, Qt.AlignCenter, "🔒")
        p.setClipping(False)
        # 枠（ホバー時ははっきり明るい太枠＋外側のグロー）
        p.setBrush(Qt.NoBrush)
        if self._hover:
            pen = p.pen()
            pen.setColor(QColor(80, 175, 255, 90))   # 外側グロー
            pen.setWidth(6)
            p.setPen(pen)
            p.drawRoundedRect(3, 3, tw - 6, th - 6, 11, 11)
            pen.setColor(QColor(60, 160, 255))       # 芯の明るい青
            pen.setWidth(3)
            p.setPen(pen)
            p.drawRoundedRect(2, 2, tw - 4, th - 4, 10, 10)
        else:
            pen = p.pen()
            pen.setColor(QColor(110, 116, 128))
            pen.setWidth(1)
            p.setPen(pen)
            p.drawRoundedRect(1, 1, tw - 2, th - 2, 10, 10)
        p.setPen(Qt.NoPen)
        # 価格/お試しバッジ（未購入のみ・文字は最小限）
        if not self.owned:
            badge = ("¥{}".format(self.price) if self.price else t("store_get"))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(40, 44, 52, 210))
            bw = 56
            p.drawRoundedRect(tw - bw - 6, 6, bw, 20, 7, 7)
            p.setPen(QColor(255, 230, 140))
            f = p.font(); f.setPointSize(9); f.setBold(True); p.setFont(f)
            p.drawText(tw - bw - 6, 6, bw, 20, Qt.AlignCenter, badge)
            p.setPen(Qt.NoPen)

        # お気に入りハート（ホバー中 or お気に入り済みのとき表示・メルカリ風）
        if self._hover or self.favorited:
            hx, hy = self._heart_center()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(34, 34, 34, 150))   # 背景の丸
            p.drawEllipse(QPoint(hx, hy), self.HEART_R, self.HEART_R)
            self._draw_heart(p, hx, hy, 7.5, self.favorited)
        p.end()

    def _draw_heart(self, p, cx, cy, s, filled):
        """小さなハート（2円＋三角の合成）。filled=赤塗り / それ以外=白枠"""
        heart = QPainterPath()
        heart.addEllipse(QPoint(int(cx - s * 0.5), int(cy - s * 0.35)),
                         s * 0.6, s * 0.6)
        heart.addEllipse(QPoint(int(cx + s * 0.5), int(cy - s * 0.35)),
                         s * 0.6, s * 0.6)
        tri = QPainterPath()
        tri.moveTo(cx - s * 1.0, cy - s * 0.1)
        tri.lineTo(cx + s * 1.0, cy - s * 0.1)
        tri.lineTo(cx, cy + s * 1.05)
        tri.closeSubpath()
        heart = heart.united(tri)
        if filled:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 150, 90))   # お気に入り＝あたたかい山吹/コーラル（赤ではない）
        else:
            pen = p.pen()
            pen.setColor(QColor(255, 255, 255))
            pen.setWidth(2)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
        p.drawPath(heart)
        p.setPen(Qt.NoPen)


class SettingsDialog(QDialog):
    stats_received = pyqtSignal(object)   # 人気投票の集計（別スレッド→UI）

    def __init__(self, config, on_apply, on_save, on_load, on_language_change=None, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.on_apply = on_apply
        self.on_language_change = on_language_change
        self.on_save = on_save
        self.on_load = on_load
        self.setWindowTitle("1/f - 設定")
        self._build_ui()

    def _apply_skin(self, skin=None):
        skin = skin or self.config.get("ui_skin", DEFAULT_SKIN)
        self.setStyleSheet(UI_SKINS.get(skin, UI_SKINS[DEFAULT_SKIN]))

    def _build_ui(self):
        from PyQt5.QtWidgets import QSplitter
        self._apply_skin()   # 設定画面のスキン（テーマ）を適用
        layout = QVBoxLayout(self)
        title = QLabel(t("settings_title"))
        title.setFont(QFont("Meiryo", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # シーン選択は右の「シーン」パネル（グリッド）で行うため、選択用の
        # プルダウンは表示しない。ただし現在シーンの管理・設定タブ切替・プリセット
        # 対象の判定に使うので、ウィジェットは隠したまま保持する。
        self.scene_combo = QComboBox()
        self.scene_combo.hide()
        self._refresh_scene_combo(self.config.get("scene_mode", "grass"))
        self.scene_combo.currentIndexChanged.connect(self._on_scene_changed)
        # 現在のシーン名だけ控えめに表示
        self.current_scene_label = QLabel()
        self.current_scene_label.setAlignment(Qt.AlignCenter)
        self.current_scene_label.setStyleSheet("color:#888; font-size:11px;")
        layout.addWidget(self.current_scene_label)
        self._update_current_scene_label()

        self._initial_scene = self.config.get("scene_mode", "grass")

        # 左右レイアウト
        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        # 左: メイン設定タブ
        self.tabs = tabs = QTabWidget()
        tabs.setMinimumWidth(380)
        hbox.addWidget(tabs, 1)

        # 右: オプション・テスト・シーン（アイコングリッド）タブ
        # シーンタイル3つ＋余白がスクロールせず横に並ぶ幅を確保
        tabs2 = QTabWidget()
        tabs2.setMinimumWidth(440)
        hbox.addWidget(tabs2, 1)

        # === シーン別設定タブ（各シーンモジュールが build_settings で提供） ===
        # key -> [(widget, タブ名), ...]。表示は _update_tabs_for_scene が行う
        self._scene_tabs = {}
        for info in scene_registry():
            builder = info.get("build_settings")
            if not builder:
                self._scene_tabs[info["key"]] = []
                continue
            try:
                self._scene_tabs[info["key"]] = builder(self)
            except Exception:
                # 1シーンのタブ構築失敗で設定画面全体を道連れにしない
                import traceback
                traceback.print_exc()
                self._scene_tabs[info["key"]] = []

        # === タブ: 環境 ===
        tab_env = QWidget()
        tel = QVBoxLayout(tab_env)

        g4 = QGroupBox(t("wind_strength"))
        g4l = QVBoxLayout(g4)
        self.wind_slider = self._add_slider(g4l, t("wind"), 0, 100, self.config.get("wind", 50))
        self.sway_speed_slider = self._add_slider(g4l, t("sway_speed"), 5, 100, self.config.get("sway_speed", 50))
        tel.addWidget(g4)

        gm = QGroupBox(t("mouse_fade"))
        gml = QVBoxLayout(gm)
        self.mouse_fade_btn = QPushButton("ON" if self.config.get("mouse_fade_enabled", True) else "OFF")
        self.mouse_fade_btn.setCheckable(True)
        self.mouse_fade_btn.setChecked(self.config.get("mouse_fade_enabled", True))
        self.mouse_fade_btn.toggled.connect(lambda c: self.mouse_fade_btn.setText("ON" if c else "OFF"))
        gml.addWidget(self.mouse_fade_btn)
        self.fade_inner_slider = self._add_slider(gml, t("fade_center"), 0, 200, self.config.get("mouse_fade_inner", 30))
        self.fade_range_slider = self._add_slider(gml, t("fade_range"), 10, 500, self.config.get("mouse_fade_range", 120))
        self.fade_alpha_slider = self._add_slider(gml, t("fade_alpha"), 0, 200, self.config.get("mouse_fade_alpha", 15))
        fade_desc = QLabel(t("fade_desc"))
        fade_desc.setStyleSheet("color: #666; font-size: 10px;")
        fade_desc.setWordWrap(True)
        gml.addWidget(fade_desc)
        tel.addWidget(gm)

        # 起動時のモード抽選（お気に入り登録）
        g_boot = QGroupBox(t("startup_mode"))
        g_bl = QVBoxLayout(g_boot)
        self.startup_random_check = QCheckBox(t("startup_random"))
        self.startup_random_check.setChecked(self.config.get("startup_random", True))
        self.startup_random_check.toggled.connect(self._on_slider_changed)
        g_bl.addWidget(self.startup_random_check)
        boot_desc = QLabel(t("startup_random_desc"))
        boot_desc.setStyleSheet("color: #666; font-size: 10px;")
        boot_desc.setWordWrap(True)
        g_bl.addWidget(boot_desc)
        saved_pool = self.config.get("startup_scenes") or [k for k, _ in scene_modes()]
        self.startup_scene_checks = []
        for key, label_key in scene_modes():
            cb = QCheckBox(_scene_label(key, label_key))
            cb.setChecked(key in saved_pool)
            cb.toggled.connect(self._on_slider_changed)
            g_bl.addWidget(cb)
            self.startup_scene_checks.append((key, cb))
        tel.addWidget(g_boot)

        g_startup = QGroupBox(t("system"))
        g_sl = QVBoxLayout(g_startup)
        self.startup_check = QCheckBox(t("auto_startup"))
        self.startup_check.setChecked(is_startup_enabled())
        self.startup_check.toggled.connect(lambda c: set_startup_enabled(c))
        g_sl.addWidget(self.startup_check)
        self.auto_update_check = QCheckBox(t("auto_update"))
        self.auto_update_check.setChecked(self.config.get("auto_update", True))
        self.auto_update_check.toggled.connect(self._on_slider_changed)
        g_sl.addWidget(self.auto_update_check)
        tel.addWidget(g_startup)

        tabs.addTab(tab_env, t("tab_env"))

        # === タブ4: オプション ===
        tab_opt = QWidget()
        tol = QVBoxLayout(tab_opt)

        g_light = QGroupBox(t("lighting"))
        g_ll = QVBoxLayout(g_light)
        light_desc = QLabel(t("lighting_desc"))
        light_desc.setStyleSheet("color: #666; font-size: 11px;")
        light_desc.setWordWrap(True)
        g_ll.addWidget(light_desc)

        self.lighting_combo = QComboBox()
        self.lighting_combo.addItem(t("light_off"), "off")
        self.lighting_combo.addItem(t("light_auto"), "auto")
        self.lighting_combo.addItem(t("light_sunrise"), "sunrise")
        self.lighting_combo.addItem(t("light_daytime"), "daytime")
        self.lighting_combo.addItem(t("light_sunset"), "sunset")
        self.lighting_combo.addItem(t("light_night"), "night")
        current_mode = self.config.get("lighting_mode", "off")
        for i in range(self.lighting_combo.count()):
            if self.lighting_combo.itemData(i) == current_mode:
                self.lighting_combo.setCurrentIndex(i)
                break
        self.lighting_combo.currentIndexChanged.connect(self._on_lighting_changed)
        g_ll.addWidget(self.lighting_combo)

        # 言語切替
        g_lang = QGroupBox("Language")
        g_lang_l = QVBoxLayout(g_lang)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("日本語", "ja")
        self.lang_combo.addItem("English", "en")
        current_lang = self.config.get("language", get_language())
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current_lang:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        g_lang_l.addWidget(self.lang_combo)
        g_lang.setLayout(g_lang_l)

        # 設定画面のスキン（テーマ）
        g_skin = QGroupBox(t("skin"))
        g_skin_l = QVBoxLayout(g_skin)
        self.skin_combo = QComboBox()
        for skin_key, skin_label in (("natural", t("skin_natural")),
                                     ("dark", t("skin_dark")),
                                     ("sakura", t("skin_sakura"))):
            self.skin_combo.addItem(skin_label, skin_key)
        cur_skin = self.config.get("ui_skin", DEFAULT_SKIN)
        idx = self.skin_combo.findData(cur_skin)
        self.skin_combo.setCurrentIndex(max(idx, 0))
        self.skin_combo.currentIndexChanged.connect(self._on_skin_changed)
        g_skin_l.addWidget(self.skin_combo)

        # 天気エフェクト
        g_weather = QGroupBox(t("weather"))
        g_wl = QVBoxLayout(g_weather)
        weather_desc = QLabel(t("weather_desc"))
        weather_desc.setStyleSheet("color: #666; font-size: 11px;")
        weather_desc.setWordWrap(True)
        g_wl.addWidget(weather_desc)
        self.weather_btn = QPushButton("ON" if self.config.get("weather_enabled", True) else "OFF")
        self.weather_btn.setCheckable(True)
        self.weather_btn.setChecked(self.config.get("weather_enabled", True))
        self.weather_btn.toggled.connect(self._on_weather_toggled)
        g_wl.addWidget(self.weather_btn)


        # 風速連動
        g_wsync = QGroupBox(t("wind_sync"))
        g_wsl = QVBoxLayout(g_wsync)
        wsync_desc = QLabel(t("wind_sync_desc"))
        wsync_desc.setStyleSheet("color: #666; font-size: 11px;")
        wsync_desc.setWordWrap(True)
        g_wsl.addWidget(wsync_desc)
        self.wind_sync_btn = QPushButton("ON" if self.config.get("wind_sync_enabled", False) else "OFF")
        self.wind_sync_btn.setCheckable(True)
        self.wind_sync_btn.setChecked(self.config.get("wind_sync_enabled", False))
        self.wind_sync_btn.toggled.connect(self._on_wind_sync_toggled)
        g_wsl.addWidget(self.wind_sync_btn)
        limit_desc = QLabel(t("wind_limit_desc"))
        limit_desc.setWordWrap(True)
        limit_desc.setStyleSheet("color: #666; font-size: 10px;")
        g_wsl.addWidget(limit_desc)
        self.wind_limit_slider = self._add_slider(g_wsl, t("wind_limit"), 10, 30, self.config.get("wind_sync_limit", 15))
        limit_note = QLabel("e.g. 15 = up to 1.5x your wind setting" if get_language() == "en" else "例: 15 = あなたの風設定の最大1.5倍まで")
        limit_note.setStyleSheet("color: #888; font-size: 10px;")
        g_wsl.addWidget(limit_note)

        # サウンド連動（Windowsのみ）
        if audio_supported():
            g_ssync = QGroupBox(t("sound_sync"))
            g_ssl = QVBoxLayout(g_ssync)
            ssync_desc = QLabel(t("sound_sync_desc"))
            ssync_desc.setStyleSheet("color: #666; font-size: 11px;")
            ssync_desc.setWordWrap(True)
            g_ssl.addWidget(ssync_desc)
            self.sound_sync_btn = QPushButton("ON" if self.config.get("sound_sync_enabled", False) else "OFF")
            self.sound_sync_btn.setCheckable(True)
            self.sound_sync_btn.setChecked(self.config.get("sound_sync_enabled", False))
            self.sound_sync_btn.toggled.connect(self._on_sound_sync_toggled)
            g_ssl.addWidget(self.sound_sync_btn)
            self.sound_gain_slider = self._add_slider(g_ssl, t("sound_gain"), 10, 200, self.config.get("sound_sync_gain", 50))
            self.sound_bass_slider = self._add_slider(g_ssl, t("sound_bass"), 0, 300, self.config.get("sound_bass_gain", 100))

        tol.addWidget(g_light)
        tol.addWidget(g_weather)
        tol.addWidget(g_wsync)
        if audio_supported():
            tol.addWidget(g_ssync)
        tol.addWidget(g_lang)
        tol.addWidget(g_skin)

        tol.addStretch()
        tabs2.addTab(tab_opt, t("tab_option"))

        # === タブ5: 保存 ===
        tab_save = QWidget()
        tsl = QVBoxLayout(tab_save)

        btn_row = QHBoxLayout()
        regen_btn = QPushButton(t("regenerate"))
        regen_btn.clicked.connect(self._on_regenerate)
        apply_btn = QPushButton(t("apply"))
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(regen_btn)
        btn_row.addWidget(apply_btn)
        tsl.addLayout(btn_row)

        self.scene_preset_group = QGroupBox(t("scene_preset"))
        g_sp_l = QVBoxLayout(self.scene_preset_group)
        sp_row1 = QHBoxLayout()
        save_scene_btn = QPushButton(t("save_scene"))
        save_scene_btn.clicked.connect(self._on_save_scene)
        sp_row1.addWidget(save_scene_btn)
        g_sp_l.addLayout(sp_row1)
        sp_row2 = QHBoxLayout()
        self.scene_preset_combo = QComboBox()
        self._refresh_scene_saves()
        load_scene_btn = QPushButton(t("load"))
        load_scene_btn.clicked.connect(self._on_load_scene)
        sp_row2.addWidget(self.scene_preset_combo, 1)
        sp_row2.addWidget(load_scene_btn)
        g_sp_l.addLayout(sp_row2)
        tsl.addWidget(self.scene_preset_group)

        g_save_env = QGroupBox(t("env_preset"))
        g_se_l = QVBoxLayout(g_save_env)
        se_row1 = QHBoxLayout()
        save_env_btn = QPushButton(t("save_env"))
        save_env_btn.clicked.connect(self._on_save_env)
        se_row1.addWidget(save_env_btn)
        g_se_l.addLayout(se_row1)
        se_row2 = QHBoxLayout()
        self.env_combo = QComboBox()
        self._refresh_env_saves()
        load_env_btn = QPushButton(t("load"))
        load_env_btn.clicked.connect(self._on_load_env)
        se_row2.addWidget(self.env_combo, 1)
        se_row2.addWidget(load_env_btn)
        g_se_l.addLayout(se_row2)
        tsl.addWidget(g_save_env)

        tsl.addStretch()
        tabs.addTab(tab_save, t("tab_save"))

        # === タブ: 人気投票 ===
        tab_poll = QWidget()
        tpl = QVBoxLayout(tab_poll)
        self.stats_optin_check = QCheckBox(t("stats_optin"))
        self.stats_optin_check.setChecked(self.config.get("stats_optin", False))
        self.stats_optin_check.toggled.connect(self._on_stats_optin_toggled)
        tpl.addWidget(self.stats_optin_check)
        poll_desc = QLabel(t("stats_privacy"))
        poll_desc.setStyleSheet("color: #666; font-size: 10px;")
        poll_desc.setWordWrap(True)
        tpl.addWidget(poll_desc)
        self.poll_status = QLabel("")
        self.poll_status.setStyleSheet("color: #666; font-size: 10px;")
        tpl.addWidget(self.poll_status)
        self._poll_periods = {}
        self._poll_sources = {}
        combo_row = QHBoxLayout()
        self.poll_src_combo = QComboBox()
        self.poll_src_combo.addItem(t("stats_src_fav"), "fav")
        self.poll_src_combo.addItem(t("stats_src_usage"), "usage")
        self.poll_src_combo.currentIndexChanged.connect(
            self._on_poll_source_changed)
        self.poll_src_combo.hide()
        combo_row.addWidget(self.poll_src_combo, 1)
        self.poll_period_combo = QComboBox()
        self.poll_period_combo.currentIndexChanged.connect(
            self._on_poll_period_changed)
        self.poll_period_combo.hide()
        combo_row.addWidget(self.poll_period_combo, 1)
        tpl.addLayout(combo_row)
        self.poll_graph = PollGraph()
        tpl.addWidget(self.poll_graph)
        tpl.addStretch()
        self.stats_received.connect(self._on_stats_received)
        if self.config.get("stats_optin", False):
            self.poll_status.setText(t("stats_loading"))
            stats.fetch_stats(self.config.get("stats_url"),
                              self.stats_received.emit)
        tabs.addTab(tab_poll, t("tab_poll"))

        # === タブ: シーンストア（右ペインの先頭・デフォルト表示） ===
        self._build_store_tab(tabs2)

        # === 2段目: グラフィックテスト ===
        tab_test = QWidget()
        ttl = QVBoxLayout(tab_test)

        # 天気テスト
        g_wtest = QGroupBox(t("gfx_test_weather"))
        g_wtl = QVBoxLayout(g_wtest)
        self.weather_test_combo = QComboBox()
        self.weather_test_combo.addItem("--", "auto")
        self.weather_test_combo.addItem("Clear", "clear")
        self.weather_test_combo.addItem("Drizzle", "drizzle")
        self.weather_test_combo.addItem("Rain", "rain")
        self.weather_test_combo.addItem("Rain + Wind", "rain_wind")
        self.weather_test_combo.addItem("Heavy Rain", "heavy_rain")
        self.weather_test_combo.addItem("Thunderstorm", "thunderstorm")
        self.weather_test_combo.addItem("Snow", "snow")
        self.weather_test_combo.addItem("Heavy Snow", "heavy_snow")
        self.weather_test_combo.currentIndexChanged.connect(self._on_weather_test)
        g_wtl.addWidget(self.weather_test_combo)
        ttl.addWidget(g_wtest)

        # ライティングテスト
        g_ltest = QGroupBox(t("gfx_test_lighting"))
        g_ltl = QVBoxLayout(g_ltest)
        self.lighting_test_combo = QComboBox()
        self.lighting_test_combo.addItem("--", "test_off")
        self.lighting_test_combo.addItem(t("light_sunrise"), "sunrise")
        self.lighting_test_combo.addItem(t("light_daytime"), "daytime")
        self.lighting_test_combo.addItem(t("light_sunset"), "sunset")
        self.lighting_test_combo.addItem(t("light_night"), "night")
        self.lighting_test_combo.currentIndexChanged.connect(self._on_lighting_test)
        g_ltl.addWidget(self.lighting_test_combo)
        ttl.addWidget(g_ltest)

        ttl.addStretch()
        tabs2.addTab(tab_test, t("tab_gfx_test"))

        # 初期シーンに応じてタブ表示を調整
        self._update_tabs_for_scene(self._initial_scene)
        # シーングリッド3列が見える初期サイズ
        self.resize(900, 580)

    def _on_sound_sync_toggled(self, checked):
        self.sound_sync_btn.setText("ON" if checked else "OFF")
        self.on_apply({"sound_sync_enabled": checked})

    def _on_wind_sync_toggled(self, checked):
        self.wind_sync_btn.setText("ON" if checked else "OFF")
        self.on_apply({"wind_sync_enabled": checked})

    def _on_weather_toggled(self, checked):
        self.weather_btn.setText("ON" if checked else "OFF")
        self.on_apply({"weather_enabled": checked})

    def _on_weather_test(self):
        state = self.weather_test_combo.currentData()
        if state == "auto":
            return
        self.on_apply({"_weather_test": state})

    def _on_lighting_test(self):
        mode = self.lighting_test_combo.currentData()
        if mode == "test_off":
            # オプションの設定に戻す
            self.on_apply({"_lighting_test": None})
        else:
            self.on_apply({"_lighting_test": mode})

    def _on_language_changed(self):
        lang = self.lang_combo.currentData()
        set_language(lang)
        self.on_apply({"language": lang})
        # 言語を即時反映: ダイアログとトレイメニューを作り直す
        if self.on_language_change:
            self.on_language_change()

    def _on_skin_changed(self):
        skin = self.skin_combo.currentData()
        self.config["ui_skin"] = skin
        self._apply_skin(skin)               # 即時反映
        self.on_apply({"ui_skin": skin})     # 保存のみ（再構築なし）

    def _add_slider(self, layout, label, min_val, max_val, current):
        row = QHBoxLayout()
        lbl = QLabel(label)
        # 固定幅だと長いラベルが切れてスライダーに隠れるため、最小幅のみ指定
        lbl.setMinimumWidth(50)
        slider = NoWheelSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(current)
        val_lbl = QLabel(str(current))
        val_lbl.setFixedWidth(35)
        slider.valueChanged.connect(lambda v: val_lbl.setText(str(v)))
        slider.valueChanged.connect(self._on_slider_changed)
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        row.addWidget(val_lbl)
        layout.addLayout(row)
        return slider

    def _on_slider_changed(self):
        cfg = self._gather_config()
        self.on_apply(cfg)

    # --- 人気投票（みんなのお気に入りモード） ---
    def _stats_uid(self):
        """匿名ID（ランダム32桁hex）。初回オプトイン時に生成して保存。
        uuid モジュールは旧スケルトン(v1)に同梱されていないため os.urandom を使う"""
        uid = self.config.get("stats_uid")
        if not uid:
            uid = os.urandom(16).hex()
            self.config["stats_uid"] = uid
        return uid

    def _favorite_scenes(self):
        return [k for k, cb in self.startup_scene_checks if cb.isChecked()]

    def _on_stats_optin_toggled(self, checked):
        if checked:
            self._stats_uid()
        self._on_slider_changed()
        if checked:
            self.poll_status.setText(t("stats_loading"))
            scenes = self._favorite_scenes()
            if scenes:
                stats.submit_favorites(self._stats_uid(), scenes,
                                       self.config.get("stats_url"),
                                       self.stats_received.emit)
            else:
                stats.fetch_stats(self.config.get("stats_url"),
                                  self.stats_received.emit)
        else:
            self.poll_status.setText("")
            self.poll_src_combo.hide()
            self.poll_period_combo.hide()
            self.poll_graph.clear()

    # 期間（データのある期間だけコンボに出す。累計は常時）
    POLL_PERIODS = [
        ("today", "stats_p_today"), ("week", "stats_p_week"),
        ("month", "stats_p_month"), ("month3", "stats_p_month3"),
        ("month6", "stats_p_month6"), ("year", "stats_p_year"),
        ("total", "stats_p_total"),
    ]

    def _on_stats_received(self, data):
        if not self.stats_optin_check.isChecked():
            return
        if not data:
            self.poll_status.setText(t("stats_failed"))
            self.poll_src_combo.hide()
            self.poll_period_combo.hide()
            self.poll_graph.clear()
            return
        self.poll_status.setText("")
        self._poll_sources = {
            "fav": data.get("periods") or {"total": data.get("counts", {})},
            "usage": data.get("usage") or {},
        }
        self.poll_src_combo.show()
        self._on_poll_source_changed()

    def _on_poll_source_changed(self):
        src = self.poll_src_combo.currentData() or "fav"
        self._poll_periods = self._poll_sources.get(src) or {}
        cur = self.poll_period_combo.currentData()
        self.poll_period_combo.blockSignals(True)
        self.poll_period_combo.clear()
        for key, label_key in self.POLL_PERIODS:
            if key == "total" or self._poll_periods.get(key):
                self.poll_period_combo.addItem(t(label_key), key)
        idx = self.poll_period_combo.findData(cur)
        self.poll_period_combo.setCurrentIndex(max(idx, 0))
        self.poll_period_combo.blockSignals(False)
        self.poll_period_combo.show()
        self._on_poll_period_changed()

    def _on_poll_period_changed(self):
        key = self.poll_period_combo.currentData()
        if key:
            self.poll_graph.set_counts(self._poll_periods.get(key, {}))

    def done(self, r):
        # 閉じるときに最新のお気に入りを投票（オプトイン時のみ・失敗は無視）
        if getattr(self, "stats_optin_check", None) and \
                self.stats_optin_check.isChecked():
            scenes = self._favorite_scenes()
            if scenes:
                stats.submit_favorites(self._stats_uid(), scenes,
                                       self.config.get("stats_url"))
        super().done(r)

    def _gather_config(self):
        cfg = {
            "wind": self.wind_slider.value(),
            "auto_update": self.auto_update_check.isChecked(),
            "startup_random": self.startup_random_check.isChecked(),
            "startup_scenes": [k for k, cb in self.startup_scene_checks
                               if cb.isChecked()],
            "stats_optin": self.stats_optin_check.isChecked(),
            "mouse_fade_enabled": self.mouse_fade_btn.isChecked(),
            "mouse_fade_inner": self.fade_inner_slider.value(),
            "mouse_fade_range": self.fade_range_slider.value(),
            "mouse_fade_alpha": self.fade_alpha_slider.value(),
            "lighting_mode": self.lighting_combo.currentData(),
            "weather_enabled": self.weather_btn.isChecked(),
            "wind_sync_enabled": self.wind_sync_btn.isChecked(),
            "wind_sync_limit": self.wind_limit_slider.value(),
            "language": self.lang_combo.currentData(),
            "scene_mode": self.scene_combo.currentData(),
            "sway_speed": self.sway_speed_slider.value(),
        }
        # シーン別設定（各シーンモジュールの gather から収集）
        for info in scene_registry():
            gather = info.get("gather")
            if not gather:
                continue
            try:
                cfg.update(gather(self))
            except Exception:
                # 1シーンの不具合で設定保存全体を壊さない
                import traceback
                traceback.print_exc()
        # サウンド連動（Windowsのみウィジェットが存在する）
        if hasattr(self, "sound_sync_btn"):
            cfg["sound_sync_enabled"] = self.sound_sync_btn.isChecked()
            cfg["sound_sync_gain"] = self.sound_gain_slider.value()
            cfg["sound_bass_gain"] = self.sound_bass_slider.value()
        # 人気投票の匿名ID（初回オプトイン時に生成済みなら永続化）
        if self.config.get("stats_uid"):
            cfg["stats_uid"] = self.config["stats_uid"]
        return cfg

    def _refresh_scene_combo(self, select_key=None):
        """シーン一覧コンボを作り直す（入手・期限切れでモードが増減したとき）。
        期間限定モードの自動出現/消滅に追従するため都度 scene_modes() を呼ぶ"""
        if select_key is None:
            select_key = self.scene_combo.currentData()
        self.scene_combo.blockSignals(True)
        self.scene_combo.clear()
        for mode_key, label_key in scene_modes():
            self.scene_combo.addItem(_scene_label(mode_key, label_key), mode_key)
        idx = self.scene_combo.findData(select_key)
        self.scene_combo.setCurrentIndex(max(idx, 0))
        self.scene_combo.blockSignals(False)
        self._update_current_scene_label()

    def _update_current_scene_label(self):
        if getattr(self, "current_scene_label", None) is None:
            return
        key = self.scene_combo.currentData()
        name = next((_scene_label(k, lk) for k, lk in scene_modes() if k == key),
                    key or "")
        self.current_scene_label.setText(t("current_scene").format(name=name))

    def _on_scene_changed(self):
        scene = self.scene_combo.currentData()
        self._update_tabs_for_scene(scene)
        self._refresh_scene_saves()
        self._update_current_scene_label()
        self.on_apply({"scene_mode": scene})

    def _update_tabs_for_scene(self, scene):
        """シーンに応じてタブを切り替え（現在シーンのタブを先頭に挿す）"""
        tabs = self.tabs
        all_scene_widgets = {w for pairs in self._scene_tabs.values()
                             for w, _ in pairs}
        for i in range(tabs.count() - 1, -1, -1):
            if tabs.widget(i) in all_scene_widgets:
                tabs.removeTab(i)
        for i, (widget, label) in enumerate(self._scene_tabs.get(scene, [])):
            tabs.insertTab(i, widget, label)

    def _on_lighting_changed(self):
        mode = self.lighting_combo.currentData()
        self.on_apply({"lighting_mode": mode})

    def _on_regenerate(self):
        cfg = self._gather_config()
        cfg["seed"] = random.randint(0, 999999)
        self.on_apply(cfg)

    def _on_apply(self):
        cfg = self._gather_config()
        self.on_apply(cfg)

    # シーン別プリセットキーは各シーンモジュールの SCENE["preset_keys"]
    # （scenes.get_preset_keys で取得）
    # 環境設定のキー
    ENV_KEYS = [
        "wind", "sway_speed", "mouse_fade_enabled", "mouse_fade_inner",
        "mouse_fade_range", "mouse_fade_alpha", "lighting_mode",
        "weather_enabled", "wind_sync_enabled", "wind_sync_limit",
        "sound_sync_enabled", "sound_sync_gain", "sound_bass_gain",
        "startup_random", "startup_scenes",
    ]

    def _on_save_scene(self):
        scene = self.scene_combo.currentData()
        keys = get_preset_keys(scene)
        cfg = self._gather_config()
        self.on_save(scene, {k: cfg[k] for k in keys if k in cfg})
        self._refresh_scene_saves()

    def _on_load_scene(self):
        name = self.scene_preset_combo.currentText()
        scene = self.scene_combo.currentData()
        if name:
            self.on_load(scene, name)

    def _on_save_env(self):
        cfg = self._gather_config()
        self.on_save("env", {k: cfg[k] for k in self.ENV_KEYS if k in cfg})
        self._refresh_env_saves()

    def _on_load_env(self):
        name = self.env_combo.currentText()
        if name:
            self.on_load("env", name)

    # --- シーンストア（アイコングリッド: ライブプレビュー・クリック再生・お試し） ---
    def _build_store_tab(self, tabs):
        from PyQt5.QtWidgets import QScrollArea, QGridLayout
        tab = QWidget()
        outer = QVBoxLayout(tab)
        desc = QLabel(t("store_desc"))
        desc.setStyleSheet("color: #666; font-size: 10px;")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self.store_grid_host = QWidget()
        self.store_grid = QGridLayout(self.store_grid_host)
        self.store_grid.setSpacing(8)
        outer.addWidget(self.store_grid_host)

        refresh = QPushButton(t("store_refresh"))
        refresh.clicked.connect(self._reload_store)
        outer.addWidget(refresh)
        outer.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(scroll)
        # 右ペインの先頭に置き、設定を開いたとき最初にショップが見える
        tabs.insertTab(0, holder, t("tab_store"))
        tabs.setCurrentIndex(0)
        self._reload_store()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _reload_store(self):
        from scenes import _collab
        lang = get_language()
        self._clear_layout(self.store_grid)
        favs = set(self.config.get("scene_favorites") or [])
        tiles = []
        # 所有: 基本シーン（同梱）＋入手済みコラボ → クリックで再生
        owned = _collab.list_installed()
        owned_keys = {o["key"] for o in owned}
        for mode_key, label_key in scene_modes():
            tiles.append(SceneTile(
                mode_key, t(label_key), True, 0, None,
                self._on_tile_play, self._on_tile_trial,
                favorited=(mode_key in favs), on_favorite=self._on_tile_favorite))
        # 未購入: カタログのうち未所持 → プレビュー＋お試し（10秒）
        catalog = _collab.fetch_catalog(self.config.get("store_catalog_url"))
        for c in catalog:
            if c.get("key") in owned_keys or c.get("key") in dict(scene_modes()):
                continue
            name = (c.get("name") or {})
            nm = name.get(lang) or name.get("ja") or name.get("en") or c.get("key", "?")
            tiles.append(SceneTile(
                c.get("key"), nm, False, int(c.get("price") or 0), c.get("url"),
                self._on_tile_play, self._on_tile_trial,
                favorited=(c.get("key") in favs), on_favorite=self._on_tile_favorite))
        # お気に入りを先頭に（メルカリのお気に入り上位表示風）
        tiles.sort(key=lambda tl: not tl.favorited)
        # グリッド配置（3列）
        cols = 3
        for i, tile in enumerate(tiles):
            self.store_grid.addWidget(tile, i // cols, i % cols)

    def _on_tile_favorite(self, key, on):
        """ハートのトグル: お気に入りを config に保存（再描画はしない）"""
        favs = list(self.config.get("scene_favorites") or [])
        if on and key not in favs:
            favs.append(key)
        elif not on and key in favs:
            favs.remove(key)
        self.config["scene_favorites"] = favs
        self.on_apply({"_favorite": favs})

    def _on_tile_play(self, key):
        """所有シーンのタイルをクリック → そのシーンを再生（適用）"""
        idx = self.scene_combo.findData(key)
        if idx >= 0:
            self.scene_combo.setCurrentIndex(idx)  # コンボ経由で適用＋タブ更新
        else:
            self.on_apply({"scene_mode": key})

    def _on_tile_trial(self, key, url):
        """未購入シーンのタイルをクリック → 10秒お試し"""
        if url:
            self.on_apply({"_trial": {"key": key, "url": url}})

    def _on_install(self, url):
        from PyQt5.QtWidgets import QMessageBox
        from scenes import _collab
        if not url:
            return
        try:
            _collab.install_scene(url)
        except Exception as e:
            QMessageBox.warning(self, t("tab_store"),
                                t("store_get_failed").format(err=str(e)))
            return
        # 入手後: 一覧を作り直し、シーンコンボにも反映、ストアタブも更新
        self.on_apply({"_rescan": True})
        self._refresh_scene_combo()
        self._reload_store()

    def _on_purchase(self, c):
        """有料シーンの購入。決済は liplico store（後段）。
        store_purchase_url が設定されていれば購入トークン経由で入手する想定。
        未稼働なら「準備中」を案内する。"""
        from PyQt5.QtWidgets import QMessageBox
        purchase_url = self.config.get("store_purchase_url")
        if not purchase_url:
            QMessageBox.information(self, t("tab_store"), t("store_not_ready"))
            return
        # 後段: purchase_url に key/購入トークンを渡して DL URL を得て install。
        # liplico store 実装まではここに到達しない（差込口）。
        QMessageBox.information(self, t("tab_store"), t("store_not_ready"))

    def _on_uninstall(self, key):
        from scenes import _collab
        _collab.uninstall(key)
        self.on_apply({"_rescan": True})
        self._refresh_scene_combo()
        self._reload_store()

    def _refresh_scene_saves(self):
        self.scene_preset_combo.clear()
        scene = self.scene_combo.currentData()
        scene_dir = os.path.join(SAVE_DIR, scene)
        if os.path.exists(scene_dir):
            for f in sorted(os.listdir(scene_dir)):
                if f.endswith(".json"):
                    self.scene_preset_combo.addItem(f[:-5])
        # Update group title（シーンが preset_label_key を持てばそれを使う）
        label_key = get_scene_info(scene).get("preset_label_key", "scene_preset")
        self.scene_preset_group.setTitle(t(label_key))

    def _refresh_env_saves(self):
        self.env_combo.clear()
        env_dir = os.path.join(SAVE_DIR, "env")
        if os.path.exists(env_dir):
            for f in sorted(os.listdir(env_dir)):
                if f.endswith(".json"):
                    self.env_combo.addItem(f[:-5])


# --- 1画面分のオーバーレイ ---
class BackgroundOverlay(QWidget):
    """Separate window for background elements (Mt. Fuji) — behind other windows"""
    def __init__(self, parent_overlay):
        super().__init__()
        self.parent_overlay = parent_overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setup(self):
        set_click_through(int(self.winId()))
        set_behind_windows(int(self.winId()))

    def paintEvent(self, event):
        po = self.parent_overlay
        if not po.scene or not po.scene.has_background_layer():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        lighting_mode = po.config.get("lighting_mode", "off")
        if lighting_mode == "auto":
            tint = _get_time_tint()
        elif lighting_mode in LIGHTING_PRESETS:
            tint = LIGHTING_PRESETS[lighting_mode]
        else:
            tint = None
        get_alpha = None
        if po.config.get("mouse_fade_enabled", True):
            mx, my = get_cursor_pos()
            inner_r = po.config.get("mouse_fade_inner", 30)
            fade_r = po.config.get("mouse_fade_range", 120)
            min_alpha = po.config.get("mouse_fade_alpha", 15)
            gy = self.y() + po.ground_y // 2
            widget_x = self.x()
            def get_alpha(base_x):
                gx = widget_x + base_x
                dist = math.sqrt((mx - gx) ** 2 + (my - gy) ** 2)
                if dist <= inner_r:
                    return min_alpha
                elif dist <= inner_r + fade_r:
                    t_val = (dist - inner_r) / fade_r
                    return int(min_alpha + (255 - min_alpha) * t_val)
                return 255
        po.scene.draw_background(painter, po.ground_y, tint, get_alpha)
        painter.end()


class ScreenOverlay(QWidget):
    def __init__(self, screen, config, wind_sim):
        super().__init__()
        self.screen = screen
        self.config = config
        self.wind_sim = wind_sim
        self.weather_fx = WeatherEffect()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scene = None
        self.bg_overlay = None
        self._position_window()
        self._rebuild_scene()
        self.show()
        QTimer.singleShot(100, self._set_click_through)

    def _set_click_through(self):
        set_click_through(int(self.winId()))

    def _position_window(self):
        full = self.screen.geometry()
        avail = self.screen.availableGeometry()
        taskbar_h = full.height() - avail.height()
        taskbar_top = avail.y() + avail.height()
        if taskbar_h < 10:
            taskbar_top = full.y() + full.height() - 48
        scene_cls = get_scene_class(self.config.get("scene_mode", "grass"))
        temp_scene = scene_cls()
        area_height = temp_scene.get_area_height(self.config)
        self.area_height = area_height
        self.ground_y = area_height
        geo = (full.x(), taskbar_top - area_height, full.width(), area_height)
        self.setGeometry(*geo)
        ensure_topmost(int(self.winId()))
        self.weather_fx.set_geometry(full.width(), area_height)
        # Position background overlay at same geometry
        if self.bg_overlay:
            self.bg_overlay.setGeometry(*geo)
            QTimer.singleShot(50, self.bg_overlay.setup)

    def _rebuild_scene(self):
        scene_cls = get_scene_class(self.config.get("scene_mode", "grass"))
        self.scene = scene_cls()
        screen_w = self.screen.geometry().width()
        self.scene.rebuild(self.config, screen_w, self.width())
        # Create/destroy background overlay as needed
        if self.scene.has_background_layer():
            if not self.bg_overlay:
                self.bg_overlay = BackgroundOverlay(self)
                self.bg_overlay.setGeometry(self.geometry())
                self.bg_overlay.show()
                QTimer.singleShot(50, self.bg_overlay.setup)
        else:
            if self.bg_overlay:
                self.bg_overlay.close()
                self.bg_overlay = None

    def update_scene(self):
        if self.scene:
            # 天気をシーンに伝える（雨なら旅人が傘をさす等）
            state = (self.weather_fx.current_state
                     if self.config.get("weather_enabled", True) else "clear")
            self.scene.set_weather(state)
            # Pass mouse position for interactive physics
            mx, my = get_cursor_pos()
            wx, wy = self.x(), self.y()
            local_mx = mx - wx
            local_my = my - wy
            self.scene.update(self.wind_sim, mouse_pos=(local_mx, local_my))
        self.weather_fx.update()
        self.update()
        if self.bg_overlay:
            self.bg_overlay.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        lighting_mode = self.config.get("lighting_mode", "off")
        if lighting_mode == "auto":
            tint = _get_time_tint()
        elif lighting_mode in LIGHTING_PRESETS:
            tint = LIGHTING_PRESETS[lighting_mode]
        else:
            tint = None
        get_alpha = None
        fade_enabled = self.config.get("mouse_fade_enabled", True)
        if fade_enabled:
            mx, my = get_cursor_pos()
            inner_r = self.config.get("mouse_fade_inner", 30)
            fade_r = self.config.get("mouse_fade_range", 120)
            min_alpha = self.config.get("mouse_fade_alpha", 15)
            gy = self.y() + self.ground_y // 2
            widget_x = self.x()
            def get_alpha(base_x):
                gx = widget_x + base_x
                dist = math.sqrt((mx - gx) ** 2 + (my - gy) ** 2)
                if dist <= inner_r:
                    return min_alpha
                elif dist <= inner_r + fade_r:
                    t_val = (dist - inner_r) / fade_r
                    return int(min_alpha + (255 - min_alpha) * t_val)
                return 255
        if self.scene:
            self.scene.draw(painter, self.ground_y, tint, get_alpha)
        if self.config.get("weather_enabled", True):
            self.weather_fx.draw(painter)
        painter.end()


# --- マルチモニター対応マネージャー ---
class OverlayManager:
    BASE_WIDTH = 2400
    DEFAULT_CONFIG = {
        "min_height": 4, "max_height": 20,
        "num_clusters": 5, "cluster_count": 90,
        "cluster_density": 70, "sparseness": 50,
        "scatter_count": 20, "scatter_density": 20,
        "wind": 52, "slim_ratio": 74, "flower_ratio": 44,
        "palette_indices": [0],
        "mouse_fade_enabled": True, "mouse_fade_inner": 100,
        "mouse_fade_range": 120, "mouse_fade_alpha": 0,
        "seed": 535401,
    }
    SCALE_KEYS = ["cluster_count", "scatter_count", "num_clusters"]

    def __init__(self):
        self.config = self._load_config()
        # 保存済み言語設定を反映
        saved_lang = self.config.get("language")
        if saved_lang:
            set_language(saved_lang)
        # 起動時のモード抽選: お気に入り（未設定なら全モード）からランダムに選ぶ
        # 抽選で選ばれたモードは「指名」ではないため利用記録の対象外
        self._scene_designated = True
        if self.config.get("startup_random", True):
            valid = [k for k, _ in SCENE_MODES]
            pool = [k for k in (self.config.get("startup_scenes") or valid)
                    if k in valid]
            if pool:
                self.config["scene_mode"] = random.choice(pool)
                self._scene_designated = False
        # 署名付きコラボシーンは import 時にスキャン済み。今日はもう再スキャン不要
        self._last_collab_date = time.strftime("%Y-%m-%d")
        self.collab_notifier = None  # main() がトレイ通知を差す
        self.wind_sim = WindSimulator()
        self.wind_sim.set_wind(self.config.get("wind", 50))
        self.last_time = time.monotonic()
        self.overlays = []
        self._create_overlays()

        # サウンド連動（Windowsのみ）
        self.audio_monitor = AudioLevelMonitor()
        if self.config.get("sound_sync_enabled", False):
            self.audio_monitor.start()

        # 天気監視
        self.weather_monitor = WeatherMonitor()
        self.weather_monitor.signal.updated.connect(self._on_weather_update)
        if self.config.get("weather_enabled", True):
            self.weather_monitor.start()

        self.user_visible = True
        self._fullscreen_hidden = False

        # 利用記録（人気投票オプトイン時のみ、1モード×1日につき1回）
        self._usage_sent = set()
        self._report_usage()

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(11)  # ~90fps (3x faster)

        self.reposition_timer = QTimer()
        self.reposition_timer.timeout.connect(self._refresh_screens)
        self.reposition_timer.start(5000)

        self.fullscreen_timer = QTimer()
        self.fullscreen_timer.timeout.connect(self._check_fullscreen)
        self.fullscreen_timer.start(1000)

    def _on_weather_update(self, state):
        """天気更新時に全画面のエフェクトを更新"""
        for o in self.overlays:
            o.weather_fx.set_wind_speed(state.wind_speed or 0)
            o.weather_fx.set_weather(state.weather_state)
        # 風速連動
        user_wind = self.config.get("wind", 50)
        wind_sync = self.config.get("wind_sync_enabled", False)
        if wind_sync and state.wind_speed and state.wind_speed > WIND_SPEED_CALM:
            api_wind = min(100, int(state.wind_speed * 100 / WIND_SPEED_MAX))
            # 上限: ユーザー設定の N 倍まで
            limit_mult = self.config.get("wind_sync_limit", 15) / 10.0
            max_wind = int(user_wind * limit_mult)
            self.wind_sim.set_wind(min(api_wind, max_wind))
        else:
            self.wind_sim.set_wind(user_wind)

    def _create_overlays(self):
        for o in self.overlays:
            o.close()
        self.overlays = []
        for screen in QApplication.screens():
            overlay = ScreenOverlay(screen, self.config, self.wind_sim)
            self.overlays.append(overlay)

    def _report_usage(self):
        """現在のモードの利用を記録（オプトイン時のみ）。
        ユーザーが指名したモードだけが対象（起動時の抽選は数えない）。
        同じモード×同じ日は一度しか送らない（サーバ側もupsertで重複なし）"""
        if not self._scene_designated:
            return
        if not self.config.get("stats_optin", False):
            return
        uid = self.config.get("stats_uid")
        if not uid:
            return
        scene = self.config.get("scene_mode", "grass")
        key = (scene, time.strftime("%Y-%m-%d"))
        if key in self._usage_sent:
            return
        self._usage_sent.add(key)
        stats.submit_usage(uid, scene, self.config.get("stats_url"))

    def _refresh_screens(self):
        current_screens = set(id(s) for s in QApplication.screens())
        overlay_screens = set(id(o.screen) for o in self.overlays)
        if current_screens != overlay_screens:
            self._create_overlays()
        else:
            for o in self.overlays:
                o._position_window()
        # 署名付きコラボシーンの期限チェック（日付が変わったときだけ再スキャン）。
        # 期限切れは _collab が自動削除し、ここで通知＋一覧更新する
        self._check_collab_expiry()
        # 期間限定モードの終了チェック（5秒ごと）。実行中に日付をまたいで
        # 期限が切れたら、お気に入り（無ければ草原）へ自動フォールバック
        self._check_scene_expiry()
        # 日付が変わった・モードが変わったときの利用記録（5秒ごとの軽いチェック）
        self._report_usage()

    def _check_collab_expiry(self):
        today = time.strftime("%Y-%m-%d")
        if getattr(self, "_last_collab_date", None) == today:
            return
        self._last_collab_date = today
        # 日付が変わったら失効リストも確認（権利停止・リコール）
        self._check_revocations()
        try:
            expired = scenes_registry.rescan()
        except Exception:
            return
        for name in expired:
            self._notify_scene_gone(name, "expired")

    TRIAL_SECONDS = 10

    def start_trial(self, info):
        """未購入シーンを TRIAL_SECONDS 秒だけ試す。終了後は元のシーンへ戻す。
        info = {"key":..., "url":...}（カタログの署名付きパッケージURL）。
        保存はしない（config.json を書き換えない）。"""
        from scenes import _collab
        key, url = info.get("key"), info.get("url")
        if not key or not url:
            return
        # 既に試用中なら一旦終了
        if getattr(self, "_trial_key", None):
            self.end_trial()
        try:
            tkey, src = _collab.fetch_trial(url)
            scenes_registry.register_trial(tkey, src)
        except Exception as e:
            cb = getattr(self, "collab_notifier", None)
            if cb:
                cb(str(e), "trial_failed")
            return
        # 現在のシーンを退避して試用シーンへ切替（保存しない）
        self._trial_prev_mode = self.config.get("scene_mode", "grass")
        self._trial_key = tkey
        self.config["scene_mode"] = tkey
        for o in self.overlays:
            o.config = self.config
            o._position_window()
            o._rebuild_scene()
        cb = getattr(self, "collab_notifier", None)
        if cb:
            cb(str(self.TRIAL_SECONDS), "trial_start")
        self._trial_timer = QTimer()
        self._trial_timer.setSingleShot(True)
        self._trial_timer.timeout.connect(self.end_trial)
        self._trial_timer.start(self.TRIAL_SECONDS * 1000)

    def end_trial(self):
        """お試し終了: 元のシーンへ戻し、試用シーンを登録解除する"""
        key = getattr(self, "_trial_key", None)
        if not key:
            return
        self._trial_key = None
        if getattr(self, "_trial_timer", None):
            self._trial_timer.stop()
        self.config["scene_mode"] = getattr(self, "_trial_prev_mode", "grass")
        for o in self.overlays:
            o.config = self.config
            o._position_window()
            o._rebuild_scene()
        scenes_registry.unregister(key)
        cb = getattr(self, "collab_notifier", None)
        if cb:
            cb("", "trial_end")

    def _check_revocations(self):
        """署名付き失効リストを取得し、停止対象のシーンを削除＋通知。
        買い切り（永続）シーンも後から提供停止できる。オフラインは次回適用。"""
        from scenes import _collab
        try:
            removed = _collab.fetch_and_apply_revocations(
                self.config.get("store_revoke_url"))
        except Exception:
            return
        if not removed:
            return
        try:
            scenes_registry.rescan()
        except Exception:
            pass
        for name in removed:
            self._notify_scene_gone(name, "revoked")
        # 使用中のシーンが停止された場合はお気に入りへ切替＋再描画
        self._check_scene_expiry()
        for o in self.overlays:
            o._rebuild_scene()

    def _notify_scene_gone(self, name, kind):
        """シーンが消えたことをトレイ通知（kind: expired=期間終了 / revoked=提供終了）"""
        cb = getattr(self, "collab_notifier", None)
        if cb:
            cb(name, kind)

    def _check_scene_expiry(self):
        current = self.config.get("scene_mode", "grass")
        # 期間外なら get_scene_info はデフォルトへフォールバックした辞書を返す
        if get_scene_info(current)["key"] == current:
            return
        valid = [k for k, _ in scene_modes()]
        pool = [k for k in (self.config.get("startup_scenes") or valid)
                if k in valid]
        new_mode = random.choice(pool) if pool else "grass"
        self.config["scene_mode"] = new_mode
        # 自動切替は「指名」ではない（利用統計に数えない）
        self._scene_designated = False
        self._save_config()
        for o in self.overlays:
            o.config = self.config
            o._position_window()
            o._rebuild_scene()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        screen = QApplication.primaryScreen()
        actual_width = screen.geometry().width() if screen else self.BASE_WIDTH
        ratio = actual_width / self.BASE_WIDTH
        config = self.DEFAULT_CONFIG.copy()
        for key in self.SCALE_KEYS:
            config[key] = max(1, round(config[key] * ratio))
        return config

    def _save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def apply_config(self, new_config):
        # お気に入り（ハート）の保存のみ。シーン再構築はしない
        if "_favorite" in new_config:
            self.config["scene_favorites"] = new_config["_favorite"]
            self._save_config()
            return

        # 設定画面のスキン: 保存のみ（オーバーレイには影響しない）
        if "ui_skin" in new_config and len(new_config) == 1:
            self.config["ui_skin"] = new_config["ui_skin"]
            self._save_config()
            return

        # 未購入シーンのお試し（一時DL→10秒適用→自動復帰）
        if "_trial" in new_config:
            self.start_trial(new_config["_trial"])
            return

        # シーンの入手/削除でモード一覧が変わった → 再スキャンして反映
        if new_config.get("_rescan"):
            expired = scenes_registry.rescan()
            for name in expired:
                self._notify_scene_gone(name, "expired")
            for o in self.overlays:
                o._rebuild_scene()
            return

        # テストモード（他の処理をスキップ）
        test_weather = new_config.get("_weather_test")
        if test_weather:
            if test_weather == "rain_wind":
                for o in self.overlays:
                    o.weather_fx.set_wind_speed(45)
                    o.weather_fx.set_weather("rain")
                self.wind_sim.set_wind(80)
            else:
                for o in self.overlays:
                    o.weather_fx.set_wind_speed(5)
                    o.weather_fx.set_weather(test_weather)
            return

        if "_lighting_test" in new_config:
            self._lighting_test_mode = new_config["_lighting_test"]
            # configのlighting_modeを一時上書き（テスト用）
            if self._lighting_test_mode:
                self.config["lighting_mode"] = self._lighting_test_mode
            else:
                # テスト解除 → オプション設定の値に戻す
                pass  # configはそのまま
            for o in self.overlays:
                o.config = self.config
            return

        # 設定でモードを明示的に切り替えた＝指名（利用記録の対象になる）
        new_mode = new_config.get("scene_mode")
        if new_mode and new_mode != self.config.get("scene_mode"):
            self._scene_designated = True
        self.config.update(new_config)
        self.wind_sim.set_wind(self.config.get("wind", 50))
        self._save_config()
        for o in self.overlays:
            o.config = self.config
            o._position_window()
            o._rebuild_scene()
        # 天気ON/OFF制御
        if self.config.get("weather_enabled", True):
            if not self.weather_monitor._running:
                self.weather_monitor.start()
        else:
            self.weather_monitor.stop()
            for o in self.overlays:
                o.weather_fx.set_weather("clear")
        # サウンド連動ON/OFF制御
        if self.config.get("sound_sync_enabled", False):
            self.audio_monitor.start()
        else:
            self.audio_monitor.stop()
        # モード変更・オプトイン変更を利用記録に反映
        self._report_usage()

    def save_preset(self, category, data):
        cat_dir = os.path.join(SAVE_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        self.config.update(data)
        seed = self.config.get("seed", 0)
        name = f"{category}_{seed}" if category == "grass" else f"env_{int(time.time()) % 100000}"
        path = os.path.join(cat_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._save_config()

    def load_preset(self, category, name):
        path = os.path.join(SAVE_DIR, category, f"{name}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config.update(data)
            self.wind_sim.set_wind(self.config.get("wind", 50))
            self._save_config()
            for o in self.overlays:
                o.config = self.config
                o._position_window()
                o._rebuild_scene()

    def show_all(self):
        for o in self.overlays:
            o.show()
            QTimer.singleShot(100, o._set_click_through)
            if o.bg_overlay:
                o.bg_overlay.show()
                QTimer.singleShot(150, o.bg_overlay.setup)

    def hide_all(self):
        for o in self.overlays:
            o.hide()
            if o.bg_overlay:
                o.bg_overlay.hide()

    def _check_fullscreen(self):
        if not self.user_visible:
            return
        is_fs = is_fullscreen_active()
        if is_fs:
            self._fs_confirm = getattr(self, '_fs_confirm', 0) + 1
        else:
            self._fs_confirm = 0
        if self._fs_confirm == 1:
            print(f"[FS] Fullscreen detected (confirming...)")
        # Require 3 consecutive detections (3 seconds) to avoid false triggers on click
        if self._fs_confirm >= 3 and not self._fullscreen_hidden:
            self._fullscreen_hidden = True
            for o in self.overlays:
                o.hide()
        elif self._fs_confirm == 0 and self._fullscreen_hidden:
            self._fullscreen_hidden = False
            self.show_all()

    def _tick(self):
        now = time.monotonic()
        dt = now - self.last_time
        self.last_time = now
        sway_speed = self.config.get("sway_speed", 50) / 50.0
        # サウンド連動: スピーカー出力の音量を揺らぎの強さにブレンド
        if self.config.get("sound_sync_enabled", False):
            gain = self.config.get("sound_sync_gain", 50) / 50.0
            self.wind_sim.sound_level = min(2.0, self.audio_monitor.level * gain)
            bass_gain = self.config.get("sound_bass_gain", 100) / 100.0
            # 持続レベルではなくオンセットパルス: ドン!の瞬間だけ反応する
            self.wind_sim.sound_bass = min(2.0, self.audio_monitor.bass_hit * bass_gain)
        else:
            self.wind_sim.sound_level = 0.0
            self.wind_sim.sound_bass = 0.0
        self.wind_sim.update(dt * sway_speed)
        for o in self.overlays:
            o.update_scene()


class HamburgerButton(QWidget):
    """画面左下のハンバーガーメニューボタン。
    通常はマウスが近づくとフェードアウトして消える（クリックも透過）。
    Shiftを押している間は消えずにクリックでき、メニューがボタンから展開する。
    展開後はShiftを離してもメニューは閉じない。
    サイズは現在のシーンの表示倍率に連動する。
    """

    def __init__(self, manager, menu):
        super().__init__()
        self.manager = manager
        self.menu = menu
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._opacity = 1.0
        self._clickable = False
        self._reposition()
        self.show()
        QTimer.singleShot(100, lambda: set_clickable(int(self.winId()), False))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _scale(self):
        cfg = self.manager.config
        # シーンごとの表示倍率キーは各シーンの SCENE["scale_key"]
        key = get_scale_key(cfg.get("scene_mode", "grass"))
        return cfg.get(key, 100) / 100.0

    def _size(self):
        return max(24, int(HAMBURGER_BASE * self._scale()))

    def _reposition(self):
        s = self._scale()
        size = self._size()
        margin = max(4, int(8 * s))
        avail = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(avail.x() + margin,
                         avail.y() + avail.height() - size - margin,
                         size, size)

    def _tick(self):
        # 表示倍率の変更に追従
        if self._size() != self.width():
            self._reposition()
            self.update()
        # オーバーレイ非表示・全画面時はボタンも隠す
        want_visible = self.manager.user_visible and not self.manager._fullscreen_hidden
        if want_visible != self.isVisible():
            self.setVisible(want_visible)
            if want_visible:
                QTimer.singleShot(100, lambda: set_clickable(int(self.winId()), self._clickable))
        if not want_visible:
            return
        menu_open = self.menu.isVisible()
        shift = is_shift_pressed()
        if menu_open or shift:
            target = 1.0
        else:
            mx, my = get_cursor_pos()
            c = self.geometry().center()
            near = math.hypot(mx - c.x(), my - c.y()) < self.width() * 1.6
            target = 0.0 if near else 1.0
        self._opacity += (target - self._opacity) * 0.3
        if abs(self._opacity - target) < 0.02:
            self._opacity = target
        self.setWindowOpacity(self._opacity)
        # Shift中（またはメニュー展開中）だけクリック可能にする
        clickable = bool(shift) or menu_open
        if clickable != self._clickable:
            self._clickable = clickable
            set_clickable(int(self.winId()), clickable)
        # 注意: ここで ensure_topmost を定期的に呼ぶとタスクバーが
        # z順位の競り合いに負けて消えることがあるため呼ばない
        # （WindowStaysOnTopHint だけで十分）

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # ボタンの位置から上方向にメニューを展開（スタートメニュー風）
            mh = self.menu.sizeHint().height()
            self.menu.popup(QPoint(self.x(), self.y() - mh - 4))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        r = int(w * 0.22)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 24, 28, 200))
        p.drawRoundedRect(0, 0, w, w, r, r)
        p.setBrush(QColor(235, 238, 240))
        bar_w = int(w * 0.56)
        bar_h = max(2, int(w * 0.08))
        x0 = (w - bar_w) // 2
        for i in range(3):
            y = int(w * (0.30 + 0.20 * i)) - bar_h // 2
            p.drawRect(x0, y, bar_w, bar_h)
        p.end()


def _make_rounded_pixmap(icon_path, size=44, radius_ratio=0.22):
    """QPainterPath で角丸クリッピングしたピクスマップを返す"""
    src = QPixmap(icon_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    r = size * radius_ratio
    clip.addRoundedRect(0, 0, size, size, r, r)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, src)
    p.end()
    return pix


def main():
    _setup_crash_logging()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if sys.platform == "darwin":
        setup_mac_app()

    manager = OverlayManager()
    overlay_visible = [True]

    def toggle_overlay():
        if overlay_visible[0]:
            manager.hide_all()
            manager.timer.stop()
            manager.user_visible = False
        else:
            manager.show_all()
            manager.timer.start(11)
            manager.user_visible = True
            manager._fullscreen_hidden = False
        overlay_visible[0] = not overlay_visible[0]

    hotkey = HotkeyListener(toggle_overlay)

    # 起動数秒後に更新確認（オフライン等の失敗はサイレント）
    QTimer.singleShot(4000, lambda: updater.start_update_check(manager.config))
    # 前回のエラーログがあれば、同意の上で匿名報告を提案
    QTimer.singleShot(7000, lambda: _maybe_offer_error_report(manager.config))

    icon_path = os.path.join(_resource_dir(), "icon.png")
    if os.path.exists(icon_path):
        tray_icon = QIcon(_make_rounded_pixmap(icon_path, size=44, radius_ratio=0.22))
    else:
        pixmap = QPixmap(22, 22)
        pixmap.fill(QColor(0x6b, 0xb7, 0x58))
        tray_icon = QIcon(pixmap)
    tray = QSystemTrayIcon(tray_icon, app)

    settings_dialog = None

    def open_settings():
        nonlocal settings_dialog
        if settings_dialog and settings_dialog.isVisible():
            settings_dialog.raise_()
            return
        settings_dialog = SettingsDialog(
            manager.config,
            on_apply=manager.apply_config,
            on_save=manager.save_preset,
            on_load=manager.load_preset,
            on_language_change=refresh_language,
        )
        settings_dialog.show()
        # macOS: ダイアログ表示でオーバーレイが隠れることがあるため再表示
        if sys.platform == "darwin" and overlay_visible[0]:
            manager.show_all()

    def refresh_language():
        """言語変更を即時反映: トレイメニューの文言を更新し、設定画面を同じ位置・タブで開き直す"""
        nonlocal settings_dialog
        toggle_action.setText(f"{t('toggle')} ({hotkey_label})")
        settings_action.setText(t("settings"))
        regen_action.setText(t("regenerate"))
        quit_action.setText(t("quit"))
        tray.setToolTip(t("tooltip").format(hotkey=hotkey_label))
        if settings_dialog and settings_dialog.isVisible():
            pos = settings_dialog.pos()
            tab_i = settings_dialog.tabs.currentIndex()
            settings_dialog.close()
            settings_dialog = None
            open_settings()
            settings_dialog.move(pos)
            settings_dialog.tabs.setCurrentIndex(tab_i)

    menu = QMenu()
    hotkey_label = "Cmd+Ctrl+Shift+W" if sys.platform == "darwin" else "Win+Ctrl+Shift+W"
    toggle_action = QAction(f"{t('toggle')} ({hotkey_label})")
    toggle_action.triggered.connect(toggle_overlay)
    menu.addAction(toggle_action)
    settings_action = QAction(t("settings"))
    settings_action.triggered.connect(open_settings)
    menu.addAction(settings_action)
    regen_action = QAction(t("regenerate"))
    regen_action.triggered.connect(lambda: manager.apply_config({"seed": random.randint(0, 999999)}))
    menu.addAction(regen_action)
    menu.addSeparator()
    quit_action = QAction(t("quit"))
    quit_action.triggered.connect(lambda: (hotkey.cleanup(), app.quit()))
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.setToolTip(t("tooltip").format(hotkey=hotkey_label))
    tray.activated.connect(lambda reason: open_settings() if reason == QSystemTrayIcon.DoubleClick else None)
    tray.show()

    # シーンの状態変化をトレイ通知（期間終了 / 提供終了 / お試し）
    def _notify_scene_gone(name, kind="expired"):
        if kind == "revoked":
            title, body = t("collab_revoked_title"), t("collab_revoked_body")
        elif kind == "trial_start":
            title, body = t("trial_start_title"), t("trial_start_body")
        elif kind == "trial_end":
            title, body = t("trial_end_title"), t("trial_end_body")
        elif kind == "trial_failed":
            title, body = t("trial_failed_title"), t("trial_failed_body")
        else:
            title, body = t("collab_ended_title"), t("collab_ended_body")
        tray.showMessage(title, body.format(name=name, sec=name),
                         QSystemTrayIcon.Information, 5000)
    manager.collab_notifier = _notify_scene_gone
    # 起動時スキャンで既に期限切れだったコラボがあれば通知（少し遅らせて確実に表示）
    QTimer.singleShot(6000, lambda: [
        _notify_scene_gone(n, "expired") for n in scenes_registry.consume_expired()])
    # 起動後に失効リストを確認（権利停止・リコール。updater と同様オフラインは黙殺）
    QTimer.singleShot(9000, manager._check_revocations)

    # 画面左下のハンバーガーメニューボタン（トレイと同じメニューを展開）
    hamburger = HamburgerButton(manager, menu)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
