"""
1/f Yuragi - ADHDの集中支援デスクトップオーバーレイ
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
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QIcon, QPixmap, QFont, QPainterPath

# プラットフォーム固有モジュールの読み込み
if sys.platform == "win32":
    from platform_win import init_dpi, set_click_through, ensure_topmost, get_cursor_pos, HotkeyListener, is_startup_enabled, set_startup_enabled
elif sys.platform == "darwin":
    from platform_mac import init_dpi, setup_mac_app, set_click_through, ensure_topmost, get_cursor_pos, HotkeyListener, is_startup_enabled, set_startup_enabled
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

init_dpi()

from i18n import t, set_language, get_language, detect_language

def _app_dir():
    """exeの場合はexeのあるフォルダ、スクリプトの場合はスクリプトのフォルダを返す"""
    if getattr(sys, 'frozen', False):
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


class PinkNoiseGenerator:
    def __init__(self, num_octaves=8):
        self.num_octaves = num_octaves
        self.max_key = (1 << num_octaves) - 1
        self.key = 0
        self.white_values = [random.random() - 0.5 for _ in range(num_octaves)]

    def next(self):
        last_key = self.key
        self.key = (self.key + 1) & self.max_key
        diff = last_key ^ self.key
        total = 0.0
        for i in range(self.num_octaves):
            if diff & (1 << i):
                self.white_values[i] = random.random() - 0.5
            total += self.white_values[i]
        return total / (self.num_octaves * 0.5)


# --- カラーパレット ---
PALETTE_PRESETS = [
    {"name": "フォレスト",   "dark": (0x21,0x61,0x21), "mid": (0x30,0x7e,0x30), "bright": (0x6b,0xb7,0x58), "tip": (0xe4,0xfb,0x91)},
    {"name": "エメラルド",   "dark": (0x1a,0x55,0x3a), "mid": (0x28,0x80,0x5a), "bright": (0x50,0xc8,0x78), "tip": (0xa0,0xf0,0xb0)},
    {"name": "オータム",     "dark": (0x5a,0x3e,0x1a), "mid": (0x8a,0x6e,0x2a), "bright": (0xc0,0xa0,0x40), "tip": (0xf0,0xd8,0x70)},
    {"name": "オーシャン",   "dark": (0x1a,0x3a,0x5a), "mid": (0x28,0x60,0x80), "bright": (0x50,0x90,0xc0), "tip": (0x90,0xd0,0xf0)},
    {"name": "サクラ",       "dark": (0x6a,0x2a,0x3a), "mid": (0x9a,0x4a,0x5a), "bright": (0xd0,0x80,0x90), "tip": (0xf8,0xc0,0xd0)},
    {"name": "ラベンダー",   "dark": (0x3a,0x2a,0x5a), "mid": (0x5a,0x40,0x8a), "bright": (0x90,0x70,0xc0), "tip": (0xc8,0xb0,0xf0)},
    {"name": "サンセット",   "dark": (0x6a,0x2a,0x1a), "mid": (0xa0,0x50,0x20), "bright": (0xe0,0x80,0x30), "tip": (0xff,0xc0,0x60)},
    {"name": "モス",         "dark": (0x2a,0x40,0x1a), "mid": (0x4a,0x6a,0x2a), "bright": (0x7a,0x9a,0x4a), "tip": (0xb0,0xd0,0x70)},
]

FLOWER_COLORS = [
    (220, 50, 50), (255, 100, 80), (80, 80, 220), (100, 120, 255),
    (255, 220, 50), (255, 180, 200), (200, 130, 255), (255, 255, 255),
]

PIXEL_SIZE = 4


# =============================================
# プロシージャル草生成（3タイプ）
# =============================================

def _shade_for_ratio(ratio):
    if ratio < 0.3:
        return 0
    elif ratio < 0.55:
        return 1
    elif ratio < 0.8:
        return 2
    return 3


def generate_slim_grass(height, rng):
    """しゅっとした細い草: 茎のみ、枝なし、先端が細くスッと伸びる"""
    pixels = []
    # 根元は1px幅
    pixels.append((0, 0, 0))
    if height > 6:
        pixels.append((0, 1, 0))

    # 茎: 緩やかにカーブ
    curve_dir = rng.choice([-1, 1])
    curve_strength = rng.uniform(0.08, 0.25)  # 控えめなカーブ
    cx = 0.0
    start = 1 if height <= 6 else 2
    for dy in range(start, height):
        cx += curve_dir * curve_strength * (dy / height)
        dx = round(cx)
        pixels.append((dx, dy, _shade_for_ratio(dy / height)))

    return pixels, None  # 花なし


def generate_leafy_grass(height, rng):
    """葉付きの草: 茎+横に伸びる葉、花なし"""
    pixels = []
    # 根元
    root_w = 1 if height < 8 else 2
    for rdx in range(-root_w // 2, root_w // 2 + 1):
        pixels.append((rdx, 0, 0))
        if height > 5:
            pixels.append((rdx, 1, 0))

    # 茎
    curve_dir = rng.choice([-1, 1])
    curve_strength = rng.uniform(0.12, 0.35)
    cx = 0.0
    start = 1 if height <= 5 else 2
    for dy in range(start, height):
        cx += curve_dir * curve_strength * (dy / height)
        if rng.random() < 0.06:
            curve_dir *= -1
        dx = round(cx)
        pixels.append((dx, dy, _shade_for_ratio(dy / height)))

    # 葉を1〜3枚追加
    num_leaves = rng.randint(1, min(3, max(1, height // 4)))
    used_dy = set()
    for _ in range(num_leaves):
        leaf_dy = rng.randint(max(2, height // 3), height - 1)
        if leaf_dy in used_dy:
            continue
        used_dy.add(leaf_dy)
        leaf_dir = rng.choice([-1, 1])
        stem_dx = 0
        for pdx, pdy, _ in pixels:
            if pdy == leaf_dy:
                stem_dx = pdx
                break
        leaf_len = rng.randint(2, max(2, height // 3))
        lx = stem_dx
        for li in range(1, leaf_len + 1):
            lx += leaf_dir
            ly = leaf_dy + (rng.choice([0, 1]) if li < leaf_len else 1)
            shade = 3 if (ly / height) > 0.6 else 2
            pixels.append((lx, ly, shade))

    return pixels, None  # 花なし


def generate_flower_grass(height, rng):
    """花付きの草: 茎+葉+先端に花"""
    pixels = []
    root_w = 1 if height < 8 else 2
    for rdx in range(-root_w // 2, root_w // 2 + 1):
        pixels.append((rdx, 0, 0))
        if height > 5:
            pixels.append((rdx, 1, 0))

    curve_dir = rng.choice([-1, 1])
    curve_strength = rng.uniform(0.1, 0.3)
    cx = 0.0
    start = 1 if height <= 5 else 2
    for dy in range(start, height):
        cx += curve_dir * curve_strength * (dy / height)
        if rng.random() < 0.06:
            curve_dir *= -1
        dx = round(cx)
        pixels.append((dx, dy, _shade_for_ratio(dy / height)))

    # 葉を0〜2枚
    num_leaves = rng.randint(0, min(2, max(0, height // 5)))
    used_dy = set()
    for _ in range(num_leaves):
        leaf_dy = rng.randint(max(2, height // 3), height - 2)
        if leaf_dy in used_dy:
            continue
        used_dy.add(leaf_dy)
        leaf_dir = rng.choice([-1, 1])
        stem_dx = 0
        for pdx, pdy, _ in pixels:
            if pdy == leaf_dy:
                stem_dx = pdx
                break
        leaf_len = rng.randint(1, max(1, height // 4))
        lx = stem_dx
        for li in range(1, leaf_len + 1):
            lx += leaf_dir
            ly = leaf_dy + (0 if li < leaf_len else 1)
            shade = 3 if (ly / height) > 0.6 else 2
            pixels.append((lx, ly, shade))

    flower_color = rng.choice(FLOWER_COLORS)
    return pixels, flower_color


# --- 配置生成 ---
def generate_grass_data(config, screen_width):
    seed = config.get("seed", random.randint(0, 999999))
    rng = random.Random(seed)

    min_h = config.get("min_height", 4)
    max_h = config.get("max_height", 20)
    wind = config.get("wind", 50)
    palette_indices = config.get("palette_indices", [0])

    slim_pct = config.get("slim_ratio", 40)
    flower_pct = config.get("flower_ratio", 15)
    total = slim_pct + flower_pct
    if total > 100:
        slim_pct = int(slim_pct / total * 100)
        flower_pct = 100 - slim_pct

    # === 密集エリアの設定 ===
    cluster_density = config.get("cluster_density", 70) / 100.0
    cluster_count = config.get("cluster_count", 40)        # 塊に使う総本数
    num_clusters = config.get("num_clusters", 5)            # 塊の数
    # === 散在エリアの設定 ===
    scatter_density = config.get("scatter_density", 20) / 100.0
    scatter_count = config.get("scatter_count", 20)
    # === まばら具合 (塊と塊の間隔) ===
    sparseness = config.get("sparseness", 50) / 100.0

    positions = []

    def make_one(cx):
        height = rng.randint(min_h, max_h)
        pal_idx = rng.choice(palette_indices)
        sway_base = rng.uniform(0.8, 3.0) * (wind / 50)
        roll = rng.randint(0, 99)
        if roll < slim_pct:
            pixels, flower_color = generate_slim_grass(height, rng)
        elif roll < slim_pct + flower_pct:
            pixels, flower_color = generate_flower_grass(height, rng)
        else:
            pixels, flower_color = generate_leafy_grass(height, rng)
        return {
            "x": cx, "pixels": pixels, "palette_idx": pal_idx,
            "flower_color": flower_color, "sway_base": sway_base,
            "max_dy": max((p[1] for p in pixels), default=1),
        }

    # --- ステップ1: クラスターの開始位置を決める ---
    num_clusters = max(0, num_clusters)
    if num_clusters > 0 and cluster_count > 0:
        # 画面を等分して、そこからランダムにずらして配置
        per_cluster = max(1, cluster_count // num_clusters)
        remainder = cluster_count - per_cluster * num_clusters
        # 間隔のゆとり
        margin = int(sparseness * 150)
        segment = max(1, (screen_width - margin) // num_clusters)

        cd = cluster_density
        cluster_placed = 0
        for ci in range(num_clusters):
            if cluster_placed >= cluster_count:
                break
            # このクラスターの開始位置
            base_x = ci * segment + rng.randint(0, max(1, segment // 3))
            # クラスターごとにファジーな密集度 (±25%)
            local_cd = max(0.05, min(1.0, cd + rng.uniform(-0.25, 0.25)))
            local_inner_min = max(3, int(15 * (1 - local_cd * 0.8)))
            local_inner_max = max(local_inner_min + 3, int(30 * (1 - local_cd * 0.7)))
            # このクラスターに割り当てる本数もばらつかせる
            this_count = per_cluster + (1 if ci < remainder else 0)
            this_count = max(1, this_count + rng.randint(-2, 2))

            cx = base_x
            for _ in range(this_count):
                if cluster_placed >= cluster_count or cx >= screen_width:
                    break
                positions.append(make_one(cx))
                cluster_placed += 1
                cx += rng.randint(local_inner_min, local_inner_max)

    # --- ステップ2: 散在する草を画面全体に配置 ---
    sd = scatter_density
    scatter_gap_min = max(10, int(40 * (1 - sd * 0.7)))
    scatter_gap_max = max(scatter_gap_min + 10, int(100 * (1 - sd * 0.5)))

    scatter_placed = 0
    sx = rng.randint(5, 40)
    while sx < screen_width and scatter_placed < scatter_count:
        # 既存のクラスター位置と被ってもOK（自然に混ざる）
        positions.append(make_one(sx))
        scatter_placed += 1
        sx += rng.randint(scatter_gap_min, scatter_gap_max)

    # x座標でソート（描画順のため）
    positions.sort(key=lambda p: p["x"])
    return positions, seed


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

def _apply_tint(color, tint):
    """QColorにtint (r,g,b)の掛け算を適用して新しいQColorを返す"""
    if tint is None:
        return QColor(color)
    r, g, b = tint
    return QColor(
        min(255, int(color.red() * r)),
        min(255, int(color.green() * g)),
        min(255, int(color.blue() * b)),
    )


class GrassBlade:
    def __init__(self, data, palettes):
        self.base_x = data["x"]
        self.pixels = data["pixels"]
        pal = palettes[data["palette_idx"] % len(palettes)]
        self.colors = [
            QColor(*pal["dark"]), QColor(*pal["mid"]),
            QColor(*pal["bright"]), QColor(*pal["tip"]),
        ]
        fc = data["flower_color"]
        self.flower_color = QColor(*fc) if fc else None
        self.noise_gen = PinkNoiseGenerator()
        self.sway = 0.0
        self.sway_base = data["sway_base"]
        self.max_dy = data["max_dy"]

        if self.flower_color:
            top_pixel = max(self.pixels, key=lambda p: p[1])
            tdx, tdy = top_pixel[0], top_pixel[1]
            self.flower_pixels = [(tdx, tdy+1), (tdx-1, tdy+1), (tdx+1, tdy+1), (tdx, tdy+2)]
            self.max_dy = tdy + 2
        else:
            self.flower_pixels = []

    def update(self, wind_wave):
        local = self.noise_gen.next()
        self.sway = (wind_wave * 0.7 + local * 0.3) * self.sway_base

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        md = max(self.max_dy, 1)
        for dx, dy, shade in self.pixels:
            sf = dy / md
            draw_x = int(self.base_x + (dx + self.sway * sf) * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = _apply_tint(self.colors[shade], tint)
            c.setAlpha(alpha)
            painter.fillRect(draw_x, draw_y, ps, ps, c)
        if self.flower_color:
            for fx, fy in self.flower_pixels:
                sf = fy / md
                draw_x = int(self.base_x + (fx + self.sway * sf) * ps)
                draw_y = int(ground_y - (fy + 1) * ps)
                c = _apply_tint(self.flower_color, tint)
                c.setAlpha(alpha)
                painter.fillRect(draw_x, draw_y, ps, ps, c)


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
        # 突風で振幅が増える
        strength = self.base_strength * (1.0 + self.current_gust * 1.5)
        return base * strength


class NoWheelSlider(QSlider):
    """スクロール中に値が変わらないようホイールイベントを無視するスライダー"""
    def wheelEvent(self, event):
        event.ignore()

# --- 設定ダイアログ ---
from PyQt5.QtWidgets import QTabWidget, QCheckBox, QScrollArea

class SettingsDialog(QDialog):
    def __init__(self, config, on_apply, on_save, on_load, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.on_apply = on_apply
        self.on_save = on_save
        self.on_load = on_load
        self.setWindowTitle("1/f Yuragi - 設定")
        self.setFixedWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(t("settings_title"))
        title.setFont(QFont("Meiryo", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # === タブ1: 草 ===
        tab_grass = QWidget()
        tgl = QVBoxLayout(tab_grass)

        g1 = QGroupBox(t("grass_length"))
        g1l = QVBoxLayout(g1)
        self.min_h_slider = self._add_slider(g1l, t("min"), 2, 15, self.config.get("min_height", 4))
        self.max_h_slider = self._add_slider(g1l, t("max"), 5, 30, self.config.get("max_height", 20))
        tgl.addWidget(g1)

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

        g5 = QGroupBox(t("color_palette"))
        g5l = QVBoxLayout(g5)
        self.palette_checks = []
        for i, p in enumerate(PALETTE_PRESETS):
            row = QHBoxLayout()
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setStyleSheet(f"background-color: rgb{p['bright']}; border: 2px solid #333;")
            btn.setCheckable(True)
            btn.setChecked(i in self.config.get("palette_indices", [0]))
            row.addWidget(btn)
            row.addWidget(QLabel(p["name"]))
            row.addStretch()
            g5l.addLayout(row)
            self.palette_checks.append(btn)
        tgl.addWidget(g5)

        tabs.addTab(tab_grass, t("tab_grass"))

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

        tabs.addTab(tab_layout, t("tab_layout"))

        # === タブ3: 環境 ===
        tab_env = QWidget()
        tel = QVBoxLayout(tab_env)

        g4 = QGroupBox(t("wind_strength"))
        g4l = QVBoxLayout(g4)
        self.wind_slider = self._add_slider(g4l, t("wind"), 0, 100, self.config.get("wind", 50))
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
        lang_note = QLabel("* Restart settings to apply" if get_language() == "en" else "* 設定画面を開き直すと反映されます")
        lang_note.setStyleSheet("color: #888; font-size: 10px;")
        g_lang_l.addWidget(lang_note)
        g_lang.setLayout(g_lang_l)
        tol.addWidget(g_light)
        tol.addWidget(g_lang)

        tol.addStretch()
        tabs.addTab(tab_opt, t("tab_option"))

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

        g_save_grass = QGroupBox(t("grass_preset"))
        g_sg_l = QVBoxLayout(g_save_grass)
        sg_row1 = QHBoxLayout()
        save_grass_btn = QPushButton(t("save_grass"))
        save_grass_btn.clicked.connect(self._on_save_grass)
        sg_row1.addWidget(save_grass_btn)
        g_sg_l.addLayout(sg_row1)
        sg_row2 = QHBoxLayout()
        self.grass_combo = QComboBox()
        self._refresh_grass_saves()
        load_grass_btn = QPushButton(t("load"))
        load_grass_btn.clicked.connect(self._on_load_grass)
        sg_row2.addWidget(self.grass_combo, 1)
        sg_row2.addWidget(load_grass_btn)
        g_sg_l.addLayout(sg_row2)
        tsl.addWidget(g_save_grass)

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

    def _on_language_changed(self):
        lang = self.lang_combo.currentData()
        set_language(lang)
        self.on_apply({"language": lang})

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
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        row.addWidget(val_lbl)
        layout.addLayout(row)
        return slider

    def _gather_config(self):
        indices = [i for i, btn in enumerate(self.palette_checks) if btn.isChecked()]
        if not indices:
            indices = [0]
        return {
            "min_height": self.min_h_slider.value(),
            "max_height": max(self.max_h_slider.value(), self.min_h_slider.value() + 1),
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
            "mouse_fade_enabled": self.mouse_fade_btn.isChecked(),
            "mouse_fade_inner": self.fade_inner_slider.value(),
            "mouse_fade_range": self.fade_range_slider.value(),
            "mouse_fade_alpha": self.fade_alpha_slider.value(),
            "lighting_mode": self.lighting_combo.currentData(),
            "language": self.lang_combo.currentData(),
        }

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

    # 草プリセットのキー
    GRASS_KEYS = [
        "min_height", "max_height", "num_clusters", "cluster_count",
        "cluster_density", "sparseness", "scatter_count", "scatter_density",
        "slim_ratio", "flower_ratio", "palette_indices", "seed",
    ]
    # 環境設定のキー
    ENV_KEYS = [
        "wind", "mouse_fade_enabled", "mouse_fade_inner",
        "mouse_fade_range", "mouse_fade_alpha", "lighting_mode",
    ]

    def _on_save_grass(self):
        cfg = self._gather_config()
        self.on_save("grass", {k: cfg[k] for k in self.GRASS_KEYS if k in cfg})
        self._refresh_grass_saves()

    def _on_load_grass(self):
        name = self.grass_combo.currentText()
        if name:
            self.on_load("grass", name)

    def _on_save_env(self):
        cfg = self._gather_config()
        self.on_save("env", {k: cfg[k] for k in self.ENV_KEYS if k in cfg})
        self._refresh_env_saves()

    def _on_load_env(self):
        name = self.env_combo.currentText()
        if name:
            self.on_load("env", name)

    def _refresh_grass_saves(self):
        self.grass_combo.clear()
        grass_dir = os.path.join(SAVE_DIR, "grass")
        if os.path.exists(grass_dir):
            for f in sorted(os.listdir(grass_dir)):
                if f.endswith(".json"):
                    self.grass_combo.addItem(f[:-5])

    def _refresh_env_saves(self):
        self.env_combo.clear()
        env_dir = os.path.join(SAVE_DIR, "env")
        if os.path.exists(env_dir):
            for f in sorted(os.listdir(env_dir)):
                if f.endswith(".json"):
                    self.env_combo.addItem(f[:-5])


# --- 1画面分のオーバーレイ ---
class ScreenOverlay(QWidget):
    def __init__(self, screen, config, wind_sim):
        super().__init__()
        self.screen = screen
        self.config = config
        self.wind_sim = wind_sim
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.grasses = []
        self._position_window()
        self._rebuild_grasses()
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
        max_h = self.config.get("max_height", 20)
        self.grass_area_height = max(80, max_h * PIXEL_SIZE + 30)
        self.ground_y = self.grass_area_height
        self.setGeometry(
            full.x(), taskbar_top - self.grass_area_height,
            full.width(), self.grass_area_height,
        )
        # 最前面を再設定（他アプリに奪われた場合の回復）
        ensure_topmost(int(self.winId()))

    def _rebuild_grasses(self):
        width = self.width()
        palette_indices = self.config.get("palette_indices", [0])
        palettes = [PALETTE_PRESETS[i] for i in palette_indices if i < len(PALETTE_PRESETS)]
        if not palettes:
            palettes = [PALETTE_PRESETS[0]]
        # 画面幅に応じてスケーリングしたconfigで生成
        screen_w = self.screen.geometry().width()
        ratio = screen_w / 2400
        scaled_config = self.config.copy()
        for key in ["cluster_count", "scatter_count", "num_clusters"]:
            if key in scaled_config:
                scaled_config[key] = max(1, round(scaled_config[key] * ratio))
        data_list, _ = generate_grass_data(scaled_config, width)
        self.grasses = [GrassBlade(d, palettes) for d in data_list]

    def update_grasses(self):
        for g in self.grasses:
            wave = self.wind_sim.get_wave_at(g.base_x)
            g.update(wave)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        # 時間帯ライティング
        lighting_mode = self.config.get("lighting_mode", "off")
        if lighting_mode == "auto":
            tint = _get_time_tint()
        elif lighting_mode in LIGHTING_PRESETS:
            tint = LIGHTING_PRESETS[lighting_mode]
        else:
            tint = None
        fade_enabled = self.config.get("mouse_fade_enabled", True)
        if fade_enabled:
            mx, my = get_cursor_pos()
            inner_r = self.config.get("mouse_fade_inner", 30)
            fade_r = self.config.get("mouse_fade_range", 120)
            min_alpha = self.config.get("mouse_fade_alpha", 15)
            gy = self.y() + self.ground_y // 2
            for g in self.grasses:
                gx = self.x() + g.base_x
                dist = math.sqrt((mx - gx) ** 2 + (my - gy) ** 2)
                if dist <= inner_r:
                    alpha = min_alpha
                elif dist <= inner_r + fade_r:
                    t = (dist - inner_r) / fade_r
                    alpha = int(min_alpha + (255 - min_alpha) * t)
                else:
                    alpha = 255
                g.draw(painter, self.ground_y, alpha, tint)
        else:
            for g in self.grasses:
                g.draw(painter, self.ground_y, tint=tint)
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

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

        self.reposition_timer = QTimer()
        self.reposition_timer.timeout.connect(self._refresh_screens)
        self.reposition_timer.start(5000)

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
        self.config.update(new_config)
        self.wind_sim.set_wind(self.config.get("wind", 50))
        self._save_config()
        for o in self.overlays:
            o.config = self.config
            o._position_window()
            o._rebuild_grasses()

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
            if category == "grass":
                for o in self.overlays:
                    o.config = self.config
                    o._position_window()
                    o._rebuild_grasses()

    def show_all(self):
        for o in self.overlays:
            o.show()
            QTimer.singleShot(100, o._set_click_through)

    def hide_all(self):
        for o in self.overlays:
            o.hide()

    def _tick(self):
        now = time.monotonic()
        dt = now - self.last_time
        self.last_time = now
        self.wind_sim.update(dt)
        for o in self.overlays:
            o.update_grasses()


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
        else:
            manager.show_all()
            manager.timer.start(33)
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
        )
        settings_dialog.show()
        # macOS: ダイアログ表示でオーバーレイが隠れることがあるため再表示
        if sys.platform == "darwin" and overlay_visible[0]:
            manager.show_all()

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

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
