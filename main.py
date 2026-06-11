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
from PyQt5.QtCore import Qt, QTimer, QPoint
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
from scenes import get_scene_class, SCENE_MODES
from scenes.base import PinkNoiseGenerator, PIXEL_SIZE, HAMBURGER_BASE
from scenes.grass import PALETTE_PRESETS, FLOWER_COLORS_ALL, FLOWER_COLORS, get_active_flower_colors

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

# --- 設定ダイアログ ---
from PyQt5.QtWidgets import QTabWidget, QCheckBox, QScrollArea

class SettingsDialog(QDialog):
    def __init__(self, config, on_apply, on_save, on_load, on_language_change=None, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.on_apply = on_apply
        self.on_language_change = on_language_change
        self.on_save = on_save
        self.on_load = on_load
        self.setWindowTitle("1/f - 設定")
        self._build_ui()

    def _build_ui(self):
        from PyQt5.QtWidgets import QSplitter
        layout = QVBoxLayout(self)
        title = QLabel(t("settings_title"))
        title.setFont(QFont("Meiryo", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # シーンモード選択
        scene_row = QHBoxLayout()
        scene_label = QLabel(t("scene_mode"))
        scene_label.setFont(QFont("Meiryo", 10, QFont.Bold))
        self.scene_combo = QComboBox()
        for mode_key, label_key in SCENE_MODES:
            self.scene_combo.addItem(t(label_key), mode_key)
        current_scene = self.config.get("scene_mode", "grass")
        for i in range(self.scene_combo.count()):
            if self.scene_combo.itemData(i) == current_scene:
                self.scene_combo.setCurrentIndex(i)
                break
        self.scene_combo.currentIndexChanged.connect(self._on_scene_changed)
        scene_row.addWidget(scene_label)
        scene_row.addWidget(self.scene_combo, 1)
        layout.addLayout(scene_row)

        self._initial_scene = current_scene

        # 左右レイアウト
        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        # 左: メイン設定タブ
        self.tabs = tabs = QTabWidget()
        tabs.setMinimumWidth(380)
        hbox.addWidget(tabs, 1)

        # 右: オプション・テストタブ
        tabs2 = QTabWidget()
        tabs2.setMinimumWidth(320)
        hbox.addWidget(tabs2, 1)

        # === タブ1: 草 ===
        tab_grass = QWidget()
        tgl = QVBoxLayout(tab_grass)

        g1 = QGroupBox(t("grass_length"))
        g1l = QVBoxLayout(g1)
        self.min_h_slider = self._add_slider(g1l, t("min"), 2, 15, self.config.get("min_height", 4))
        self.max_h_slider = self._add_slider(g1l, t("max"), 5, 30, self.config.get("max_height", 20))
        self.thickness_slider = self._add_slider(g1l, t("thickness"), 1, 12, self.config.get("grass_thickness", 4))
        tgl.addWidget(g1)

        self.grass_scale_slider = self._add_slider(g1l, t("display_scale"), 25, 200, self.config.get("grass_scale", 100))

        g_type = QGroupBox(t("grass_type"))
        g_type_l = QVBoxLayout(g_type)
        desc = QLabel(t("type_desc"))
        desc.setStyleSheet("color: #666; font-size: 11px;")
        g_type_l.addWidget(desc)
        self.slim_slider = self._add_slider(g_type_l, t("slim"), 0, 100, self.config.get("slim_ratio", 40))
        self.flower_slider = self._add_slider(g_type_l, t("flower"), 0, 100, self.config.get("flower_ratio", 15))
        self.balance_label = QLabel()
        self.balance_label.setStyleSheet("color: #444; font-size: 11px;")
        g_type_l.addWidget(self.balance_label)
        self.slim_slider.valueChanged.connect(self._update_balance_label)
        self.flower_slider.valueChanged.connect(self._update_balance_label)
        self._update_balance_label()
        tgl.addWidget(g_type)


        # 花の色
        g_fc = QGroupBox(t("flower_colors"))
        g_fcl = QVBoxLayout(g_fc)
        self.flower_color_checks = []
        enabled_flowers = self.config.get("flower_colors_enabled", list(range(len(FLOWER_COLORS_ALL))))
        for i, fc in enumerate(FLOWER_COLORS_ALL):
            row = QHBoxLayout()
            cb = QCheckBox(t(fc["key"]))
            cb.setChecked(i in enabled_flowers)
            color_icon = QLabel()
            color_icon.setFixedSize(16, 16)
            r, g, b = fc["rgb"]
            color_icon.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #999;")
            row.addWidget(cb)
            row.addWidget(color_icon)
            row.addStretch()
            g_fcl.addLayout(row)
            self.flower_color_checks.append(cb)
        tgl.addWidget(g_fc)

        self.tab_grass = tab_grass
        self.tab_grass_label = t("tab_grass")
        tabs.addTab(tab_grass, self.tab_grass_label)

        # === タブ2: 配置 ===
        tab_layout = QWidget()
        tll = QVBoxLayout(tab_layout)

        gc = QGroupBox(t("cluster_area"))
        gcl = QVBoxLayout(gc)
        self.num_clusters_slider = self._add_slider(gcl, t("num_clusters"), 0, 20, self.config.get("num_clusters", 5))
        self.cluster_count_slider = self._add_slider(gcl, t("total_count"), 0, 150, self.config.get("cluster_count", 40))
        self.cluster_density_slider = self._add_slider(gcl, t("density"), 0, 100, self.config.get("cluster_density", 70))
        self.sparseness_slider = self._add_slider(gcl, t("spacing"), 0, 100, self.config.get("sparseness", 50))
        cd_desc = QLabel(t("cluster_desc"))
        cd_desc.setStyleSheet("color: #666; font-size: 10px;")
        gcl.addWidget(cd_desc)
        tll.addWidget(gc)

        gs = QGroupBox(t("scatter_area"))
        gsl = QVBoxLayout(gs)
        self.scatter_count_slider = self._add_slider(gsl, t("count"), 0, 150, self.config.get("scatter_count", 20))
        self.scatter_density_slider = self._add_slider(gsl, t("scatter_density"), 0, 100, self.config.get("scatter_density", 20))
        sd_desc = QLabel(t("scatter_desc"))
        sd_desc.setStyleSheet("color: #666; font-size: 10px;")
        gsl.addWidget(sd_desc)
        tll.addWidget(gs)

        self.tab_layout = tab_layout
        self.tab_layout_label = t("tab_layout")
        tabs.addTab(tab_layout, self.tab_layout_label)

        # === タブ: アクアリウム ===
        tab_aq = QWidget()
        aq_scroll = QScrollArea()
        aq_scroll.setWidgetResizable(True)
        aq_inner = QWidget()
        aq_layout = QVBoxLayout(aq_inner)

        self.aq_scale_slider = self._add_slider(aq_layout, t("display_scale"), 25, 200, self.config.get("aq_scale", 100))

        g_aq_plant = QGroupBox(t("aq_plant_length"))
        g_apl = QVBoxLayout(g_aq_plant)
        self.aq_min_h_slider = self._add_slider(g_apl, t("min"), 2, 20, self.config.get("aq_plant_min_height", 8))
        self.aq_max_h_slider = self._add_slider(g_apl, t("max"), 5, 40, self.config.get("aq_plant_max_height", 30))
        aq_layout.addWidget(g_aq_plant)

        g_aq_cluster = QGroupBox(t("aq_cluster"))
        g_acl = QVBoxLayout(g_aq_cluster)
        self.aq_cluster_count_slider = self._add_slider(g_acl, t("num_clusters"), 0, 10, self.config.get("aq_cluster_count", 3))
        self.aq_cluster_size_slider = self._add_slider(g_acl, t("total_count"), 1, 20, self.config.get("aq_cluster_size", 8))
        self.aq_cluster_density_slider = self._add_slider(g_acl, t("density"), 0, 100, self.config.get("aq_cluster_density", 70))
        aq_layout.addWidget(g_aq_cluster)

        g_aq_scatter = QGroupBox(t("aq_scatter"))
        g_asl = QVBoxLayout(g_aq_scatter)
        self.aq_scatter_count_slider = self._add_slider(g_asl, t("count"), 0, 50, self.config.get("aq_scatter_count", 15))
        self.aq_scatter_density_slider = self._add_slider(g_asl, t("scatter_density"), 0, 100, self.config.get("aq_scatter_density", 30))
        aq_layout.addWidget(g_aq_scatter)

        g_aq_fish = QGroupBox(t("aq_fish_settings"))
        g_afl = QVBoxLayout(g_aq_fish)
        self.aq_fish_count_slider = self._add_slider(g_afl, t("aq_fish_count"), 1, 20, self.config.get("aq_fish_count", 6))
        self.aq_speed_min_slider = self._add_slider(g_afl, t("aq_speed_min"), 5, 100, self.config.get("aq_fish_speed_min", 30))
        self.aq_speed_max_slider = self._add_slider(g_afl, t("aq_speed_max"), 5, 100, self.config.get("aq_fish_speed_max", 65))
        self.aq_fish_y_top_slider = self._add_slider(g_afl, t("aq_y_top"), 0, 80, self.config.get("aq_fish_y_top", 10))
        self.aq_fish_y_bottom_slider = self._add_slider(g_afl, t("aq_y_bottom"), 20, 90, self.config.get("aq_fish_y_bottom", 55))
        aq_layout.addWidget(g_aq_fish)

        aq_layout.addStretch()
        aq_scroll.setWidget(aq_inner)
        tab_aq_layout = QVBoxLayout(tab_aq)
        tab_aq_layout.setContentsMargins(0, 0, 0, 0)
        tab_aq_layout.addWidget(aq_scroll)

        self.tab_aquarium = tab_aq
        self.tab_aquarium_label = t("aq_settings")
        tabs.addTab(tab_aq, self.tab_aquarium_label)

        # === タブ: 東海道 ===
        tab_tk = QWidget()
        tk_scroll = QScrollArea()
        tk_scroll.setWidgetResizable(True)
        tk_inner = QWidget()
        tk_layout = QVBoxLayout(tk_inner)

        self.tk_scale_slider = self._add_slider(tk_layout, t("display_scale"), 25, 200, self.config.get("tk_scale", 100))

        g_tk_obj = QGroupBox(t("tk_objects"))
        g_tol = QVBoxLayout(g_tk_obj)
        self.tk_pine_slider = self._add_slider(g_tol, t("tk_pine"), 0, 10, self.config.get("tk_pine_count", 2))
        self.tk_willow_slider = self._add_slider(g_tol, t("tk_willow_item"), 0, 10, self.config.get("tk_willow_count", 2))
        self.tk_teahouse_slider = self._add_slider(g_tol, t("tk_teahouse"), 0, 5, self.config.get("tk_teahouse_count", 2))
        self.tk_inn_slider = self._add_slider(g_tol, t("tk_inn"), 0, 5, self.config.get("tk_inn_count", 1))
        self.tk_shop_slider = self._add_slider(g_tol, t("tk_shop"), 0, 5, self.config.get("tk_shop_count", 2))
        self.tk_kura_slider = self._add_slider(g_tol, t("tk_kura"), 0, 5, self.config.get("tk_kura_count", 1))
        self.tk_house_slider = self._add_slider(g_tol, t("tk_house"), 0, 10, self.config.get("tk_house_count", 3))
        self.tk_torii_slider = self._add_slider(g_tol, t("tk_torii"), 0, 3, self.config.get("tk_torii_count", 0))
        self.tk_hill_slider = self._add_slider(g_tol, t("tk_hill"), 0, 5, self.config.get("tk_hill_count", 2))
        self.tk_grass_slider = self._add_slider(g_tol, t("tk_grass"), 0, 150, self.config.get("tk_grass_count", 60))
        self.tk_traveler_slider = self._add_slider(g_tol, t("tk_traveler"), 0, 20, self.config.get("tk_traveler_count", 8))
        tk_layout.addWidget(g_tk_obj)

        g_tk_willow = QGroupBox(t("tk_willow"))
        g_twl = QVBoxLayout(g_tk_willow)
        self.tk_leaf_thickness_slider = self._add_slider(g_twl, t("tk_leaf_w"), 1, 6, self.config.get("tk_leaf_thickness", 4))
        self.tk_willow_min_slider = self._add_slider(g_twl, t("min"), 15, 60, self.config.get("tk_willow_min_h", 45))
        self.tk_willow_max_slider = self._add_slider(g_twl, t("max"), 30, 90, self.config.get("tk_willow_max_h", 68))
        tk_layout.addWidget(g_tk_willow)

        tk_layout.addStretch()
        tk_scroll.setWidget(tk_inner)
        tab_tk_l = QVBoxLayout(tab_tk)
        tab_tk_l.setContentsMargins(0, 0, 0, 0)
        tab_tk_l.addWidget(tk_scroll)

        self.tab_tokaido = tab_tk
        self.tab_tokaido_label = t("tk_settings")
        tabs.addTab(tab_tk, self.tab_tokaido_label)

        # === Tab: Pooh ===
        tab_pooh = QWidget()
        pooh_layout = QVBoxLayout(tab_pooh)
        self.pooh_scale_slider = self._add_slider(pooh_layout, t("display_scale"), 25, 200, self.config.get("pooh_scale", 100))
        # Character ON/OFF
        char_group = QGroupBox(t("pooh_characters"))
        char_layout = QVBoxLayout(char_group)
        self.pooh_pooh_check = QCheckBox("Winnie-the-Pooh")
        self.pooh_pooh_check.setChecked(self.config.get("pooh_show_pooh", True))
        self.pooh_pooh_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_pooh_check)
        self.pooh_tigger_check = QCheckBox("Tigger")
        self.pooh_tigger_check.setChecked(self.config.get("pooh_show_tigger", True))
        self.pooh_tigger_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_tigger_check)
        self.pooh_eeyore_check = QCheckBox("Eeyore")
        self.pooh_eeyore_check.setChecked(self.config.get("pooh_show_eeyore", True))
        self.pooh_eeyore_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_eeyore_check)
        self.pooh_piglet_check = QCheckBox("Piglet")
        self.pooh_piglet_check.setChecked(self.config.get("pooh_show_piglet", True))
        self.pooh_piglet_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_piglet_check)
        self.pooh_rabbit_check = QCheckBox("Rabbit")
        self.pooh_rabbit_check.setChecked(self.config.get("pooh_show_rabbit", True))
        self.pooh_rabbit_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_rabbit_check)
        self.pooh_owl_check = QCheckBox("Owl")
        self.pooh_owl_check.setChecked(self.config.get("pooh_show_owl", True))
        self.pooh_owl_check.toggled.connect(self._on_slider_changed)
        char_layout.addWidget(self.pooh_owl_check)
        pooh_layout.addWidget(char_group)

        self.pooh_balloon_slider = self._add_slider(pooh_layout, t("pooh_balloon_count"), 0, 400, self.config.get("pooh_balloon_count", 8))
        self.pooh_balloon_size_slider = self._add_slider(pooh_layout, t("pooh_balloon_size"), 1, 30, self.config.get("pooh_balloon_size", 30))
        self.pooh_bird_slider = self._add_slider(pooh_layout, t("pooh_bird_count"), 0, 10, self.config.get("pooh_bird_count", 3))

        # Credit notice
        credit = QLabel(t("pooh_credit"))
        credit.setWordWrap(True)
        credit.setStyleSheet("color: #888; font-size: 9px; margin-top: 8px;")
        pooh_layout.addWidget(credit)
        pooh_layout.addStretch()
        self.tab_pooh = tab_pooh
        self.tab_pooh_label = t("pooh_settings")
        tabs.addTab(tab_pooh, self.tab_pooh_label)

        # === Tab: Takibi (campfire) ===
        tab_takibi = QWidget()
        takibi_layout = QVBoxLayout(tab_takibi)
        self.takibi_scale_slider = self._add_slider(takibi_layout, t("display_scale"), 25, 200, self.config.get("takibi_scale", 100))
        self.takibi_count_slider = self._add_slider(takibi_layout, t("takibi_count"), 1, 5, self.config.get("takibi_count", 1))
        self.takibi_sparks_slider = self._add_slider(takibi_layout, t("takibi_sparks"), 0, 100, self.config.get("takibi_sparks", 25))
        self.takibi_speed_slider = self._add_slider(takibi_layout, t("takibi_speed"), 10, 100, self.config.get("takibi_speed", 30))
        self.takibi_campers_check = QCheckBox(t("takibi_campers"))
        self.takibi_campers_check.setChecked(self.config.get("takibi_campers", True))
        self.takibi_campers_check.toggled.connect(self._on_slider_changed)
        takibi_layout.addWidget(self.takibi_campers_check)
        self.takibi_tents_check = QCheckBox(t("takibi_tents"))
        self.takibi_tents_check.setChecked(self.config.get("takibi_tents", True))
        self.takibi_tents_check.toggled.connect(self._on_slider_changed)
        takibi_layout.addWidget(self.takibi_tents_check)
        self.takibi_smoke_check = QCheckBox(t("takibi_smoke"))
        self.takibi_smoke_check.setChecked(self.config.get("takibi_smoke", True))
        self.takibi_smoke_check.toggled.connect(self._on_slider_changed)
        takibi_layout.addWidget(self.takibi_smoke_check)
        self.takibi_glow_check = QCheckBox(t("takibi_glow"))
        self.takibi_glow_check.setChecked(self.config.get("takibi_glow", True))
        self.takibi_glow_check.toggled.connect(self._on_slider_changed)
        takibi_layout.addWidget(self.takibi_glow_check)
        takibi_layout.addStretch()
        self.tab_takibi = tab_takibi
        self.tab_takibi_label = t("takibi_settings")
        tabs.addTab(tab_takibi, self.tab_takibi_label)

        # === Tab: Skating (figure skating) ===
        tab_skating = QWidget()
        sk_layout = QVBoxLayout(tab_skating)
        self.skate_scale_slider = self._add_slider(sk_layout, t("display_scale"), 25, 200, self.config.get("skate_scale", 100))
        self.skate_count_slider = self._add_slider(sk_layout, t("skate_count"), 1, 5, self.config.get("skate_count", 2))
        self.skate_snow_slider = self._add_slider(sk_layout, t("skate_snow"), 0, 100, self.config.get("skate_snow", 40))
        self.skate_trail_check = QCheckBox(t("skate_trail"))
        self.skate_trail_check.setChecked(self.config.get("skate_trail", True))
        self.skate_trail_check.toggled.connect(self._on_slider_changed)
        sk_layout.addWidget(self.skate_trail_check)
        sk_layout.addStretch()
        self.tab_skating = tab_skating
        self.tab_skating_label = t("skating_settings")
        tabs.addTab(tab_skating, self.tab_skating_label)

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

        g_startup = QGroupBox(t("system"))
        g_sl = QVBoxLayout(g_startup)
        self.startup_check = QCheckBox(t("auto_startup"))
        self.startup_check.setChecked(is_startup_enabled())
        self.startup_check.toggled.connect(lambda c: set_startup_enabled(c))
        g_sl.addWidget(self.startup_check)
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

    def _update_balance_label(self):
        s = self.slim_slider.value()
        f = self.flower_slider.value()
        leafy = max(0, 100 - s - f)
        if s + f > 100:
            # 正規化表示
            total = s + f
            s_pct = int(s / total * 100)
            f_pct = 100 - s_pct
            leafy = 0
        else:
            s_pct = s
            f_pct = f
        self.balance_label.setText(
            t("balance_fmt").format(s=s_pct, l=leafy, f=f_pct)
        )

    def _add_slider(self, layout, label, min_val, max_val, current):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(50)
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

    def _gather_config(self):
        indices = self.config.get("palette_indices", [0])
        cfg = {
            "min_height": self.min_h_slider.value(),
            "max_height": max(self.max_h_slider.value(), self.min_h_slider.value() + 1),
            "grass_thickness": self.thickness_slider.value(),
            "grass_scale": self.grass_scale_slider.value(),
            "num_clusters": self.num_clusters_slider.value(),
            "cluster_count": self.cluster_count_slider.value(),
            "cluster_density": self.cluster_density_slider.value(),
            "sparseness": self.sparseness_slider.value(),
            "scatter_count": self.scatter_count_slider.value(),
            "scatter_density": self.scatter_density_slider.value(),
            "wind": self.wind_slider.value(),
            "slim_ratio": self.slim_slider.value(),
            "flower_ratio": self.flower_slider.value(),
            "palette_indices": indices,
            "flower_colors_enabled": [i for i, btn in enumerate(self.flower_color_checks) if btn.isChecked()],
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
            "aq_plant_min_height": self.aq_min_h_slider.value(),
            "aq_plant_max_height": self.aq_max_h_slider.value(),
            "aq_cluster_count": self.aq_cluster_count_slider.value(),
            "aq_cluster_size": self.aq_cluster_size_slider.value(),
            "aq_cluster_density": self.aq_cluster_density_slider.value(),
            "aq_scatter_count": self.aq_scatter_count_slider.value(),
            "aq_scatter_density": self.aq_scatter_density_slider.value(),
            "aq_fish_count": self.aq_fish_count_slider.value(),
            "aq_fish_speed_min": self.aq_speed_min_slider.value(),
            "aq_fish_speed_max": self.aq_speed_max_slider.value(),
            "aq_scale": self.aq_scale_slider.value(),
            "aq_fish_y_top": self.aq_fish_y_top_slider.value(),
            "aq_fish_y_bottom": self.aq_fish_y_bottom_slider.value(),
            "tk_pine_count": self.tk_pine_slider.value(),
            "tk_willow_count": self.tk_willow_slider.value(),
            "tk_teahouse_count": self.tk_teahouse_slider.value(),
            "tk_inn_count": self.tk_inn_slider.value(),
            "tk_shop_count": self.tk_shop_slider.value(),
            "tk_kura_count": self.tk_kura_slider.value(),
            "tk_house_count": self.tk_house_slider.value(),
            "tk_torii_count": self.tk_torii_slider.value(),
            "tk_hill_count": self.tk_hill_slider.value(),
            "tk_grass_count": self.tk_grass_slider.value(),
            "tk_traveler_count": self.tk_traveler_slider.value(),
            "tk_scale": self.tk_scale_slider.value(),
            "pooh_scale": self.pooh_scale_slider.value(),
            "pooh_show_pooh": self.pooh_pooh_check.isChecked(),
            "pooh_show_tigger": self.pooh_tigger_check.isChecked(),
            "pooh_show_eeyore": self.pooh_eeyore_check.isChecked(),
            "pooh_show_piglet": self.pooh_piglet_check.isChecked(),
            "pooh_show_rabbit": self.pooh_rabbit_check.isChecked(),
            "pooh_show_owl": self.pooh_owl_check.isChecked(),
            "pooh_balloon_count": self.pooh_balloon_slider.value(),
            "pooh_balloon_size": self.pooh_balloon_size_slider.value(),
            "pooh_bird_count": self.pooh_bird_slider.value(),
            "tk_leaf_thickness": self.tk_leaf_thickness_slider.value(),
            "tk_willow_min_h": self.tk_willow_min_slider.value(),
            "tk_willow_max_h": self.tk_willow_max_slider.value(),
            "takibi_scale": self.takibi_scale_slider.value(),
            "takibi_count": self.takibi_count_slider.value(),
            "takibi_sparks": self.takibi_sparks_slider.value(),
            "takibi_speed": self.takibi_speed_slider.value(),
            "takibi_campers": self.takibi_campers_check.isChecked(),
            "takibi_tents": self.takibi_tents_check.isChecked(),
            "takibi_smoke": self.takibi_smoke_check.isChecked(),
            "takibi_glow": self.takibi_glow_check.isChecked(),
            "skate_scale": self.skate_scale_slider.value(),
            "skate_count": self.skate_count_slider.value(),
            "skate_snow": self.skate_snow_slider.value(),
            "skate_trail": self.skate_trail_check.isChecked(),
        }
        # サウンド連動（Windowsのみウィジェットが存在する）
        if hasattr(self, "sound_sync_btn"):
            cfg["sound_sync_enabled"] = self.sound_sync_btn.isChecked()
            cfg["sound_sync_gain"] = self.sound_gain_slider.value()
            cfg["sound_bass_gain"] = self.sound_bass_slider.value()
        return cfg

    def _on_scene_changed(self):
        scene = self.scene_combo.currentData()
        self._update_tabs_for_scene(scene)
        self._refresh_scene_saves()
        self.on_apply({"scene_mode": scene})

    def _update_tabs_for_scene(self, scene):
        """シーンに応じてタブを切り替え"""
        tabs = self.tabs
        scene_tabs = [self.tab_grass, self.tab_layout, self.tab_aquarium, self.tab_tokaido, self.tab_pooh, self.tab_takibi, self.tab_skating]
        for i in range(tabs.count() - 1, -1, -1):
            if tabs.widget(i) in scene_tabs:
                tabs.removeTab(i)
        if scene == "grass":
            tabs.insertTab(0, self.tab_grass, self.tab_grass_label)
            tabs.insertTab(1, self.tab_layout, self.tab_layout_label)
        elif scene == "aquarium":
            tabs.insertTab(0, self.tab_aquarium, self.tab_aquarium_label)
        elif scene == "tokaido":
            tabs.insertTab(0, self.tab_tokaido, self.tab_tokaido_label)
        elif scene == "pooh":
            tabs.insertTab(0, self.tab_pooh, self.tab_pooh_label)
        elif scene == "takibi":
            tabs.insertTab(0, self.tab_takibi, self.tab_takibi_label)
        elif scene == "skating":
            tabs.insertTab(0, self.tab_skating, self.tab_skating_label)

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

    # シーン別プリセットキー
    SCENE_KEYS = {
        "grass": [
            "min_height", "max_height", "grass_thickness", "num_clusters", "cluster_count",
            "cluster_density", "sparseness", "scatter_count", "scatter_density",
            "slim_ratio", "flower_ratio", "palette_indices", "flower_colors_enabled", "seed",
        ],
        "aquarium": [
            "aq_plant_min_height", "aq_plant_max_height",
            "aq_cluster_count", "aq_cluster_size", "aq_cluster_density",
            "aq_scatter_count", "aq_scatter_density",
            "aq_fish_count", "aq_fish_speed_min", "aq_fish_speed_max",
            "aq_fish_y_top", "aq_fish_y_bottom", "seed",
        ],
        "pooh": ["pooh_scale", "pooh_balloon_count", "pooh_balloon_size", "pooh_bird_count", "seed"],
        "takibi": ["takibi_scale", "takibi_count", "takibi_sparks", "takibi_speed", "takibi_campers", "takibi_tents", "takibi_smoke", "takibi_glow", "seed"],
        "skating": ["skate_scale", "skate_count", "skate_snow", "skate_trail", "seed"],
        "tokaido": [
            "tk_pine_count", "tk_willow_count", "tk_teahouse_count",
            "tk_inn_count", "tk_shop_count", "tk_kura_count",
            "tk_house_count", "tk_torii_count", "tk_hill_count",
            "tk_grass_count", "tk_traveler_count",
            "tk_willow_min_h", "tk_willow_max_h", "seed",
        ],
    }
    # 環境設定のキー
    ENV_KEYS = [
        "wind", "sway_speed", "mouse_fade_enabled", "mouse_fade_inner",
        "mouse_fade_range", "mouse_fade_alpha", "lighting_mode",
        "weather_enabled", "wind_sync_enabled", "wind_sync_limit",
        "sound_sync_enabled", "sound_sync_gain", "sound_bass_gain",
    ]

    def _on_save_scene(self):
        scene = self.scene_combo.currentData()
        keys = self.SCENE_KEYS.get(scene, [])
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

    def _refresh_scene_saves(self):
        self.scene_preset_combo.clear()
        scene = self.scene_combo.currentData()
        scene_dir = os.path.join(SAVE_DIR, scene)
        if os.path.exists(scene_dir):
            for f in sorted(os.listdir(scene_dir)):
                if f.endswith(".json"):
                    self.scene_preset_combo.addItem(f[:-5])
        # Update group title
        label_map = {"grass": t("grass_preset"), "aquarium": t("aq_preset"), "tokaido": t("tokaido_preset")}
        self.scene_preset_group.setTitle(label_map.get(scene, t("scene_preset")))

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

    def _refresh_screens(self):
        current_screens = set(id(s) for s in QApplication.screens())
        overlay_screens = set(id(o.screen) for o in self.overlays)
        if current_screens != overlay_screens:
            self._create_overlays()
        else:
            for o in self.overlays:
                o._position_window()

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


# シーンごとの表示倍率キー（ハンバーガーボタンのサイズ連動用）
SCENE_SCALE_KEYS = {
    "grass": "grass_scale", "aquarium": "aq_scale", "tokaido": "tk_scale",
    "pooh": "pooh_scale", "takibi": "takibi_scale", "skating": "skate_scale",
}


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
        key = SCENE_SCALE_KEYS.get(cfg.get("scene_mode", "grass"), "grass_scale")
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

    # 画面左下のハンバーガーメニューボタン（トレイと同じメニューを展開）
    hamburger = HamburgerButton(manager, menu)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
