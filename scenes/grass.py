"""Grass scene - the original 1/f grassland"""
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtGui import QColor


# --- Color palettes ---
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

FLOWER_COLORS_ALL = [
    {"rgb": (220, 50, 50),   "key": "fc_red"},
    {"rgb": (255, 100, 80),  "key": "fc_vermilion"},
    {"rgb": (80, 80, 220),   "key": "fc_blue"},
    {"rgb": (100, 120, 255), "key": "fc_lightblue"},
    {"rgb": (255, 220, 50),  "key": "fc_yellow"},
    {"rgb": (255, 180, 200), "key": "fc_pink"},
    {"rgb": (200, 130, 255), "key": "fc_purple"},
    {"rgb": (255, 255, 255), "key": "fc_white"},
]

FLOWER_COLORS = [c["rgb"] for c in FLOWER_COLORS_ALL]


def get_active_flower_colors(config):
    enabled = config.get("flower_colors_enabled", list(range(len(FLOWER_COLORS_ALL))))
    return [FLOWER_COLORS_ALL[i]["rgb"] for i in enabled if i < len(FLOWER_COLORS_ALL)]


# --- Shade helpers ---
def _shade_for_ratio(ratio):
    if ratio < 0.3:
        return 0
    elif ratio < 0.55:
        return 1
    elif ratio < 0.8:
        return 2
    return 3


# --- Procedural grass generators ---
def generate_slim_grass(height, rng):
    pixels = []
    pixels.append((0, 0, 0))
    if height > 6:
        pixels.append((0, 1, 0))
    curve_dir = rng.choice([-1, 1])
    curve_strength = rng.uniform(0.08, 0.25)
    cx = 0.0
    start = 1 if height <= 6 else 2
    for dy in range(start, height):
        cx += curve_dir * curve_strength * (dy / height)
        dx = round(cx)
        pixels.append((dx, dy, _shade_for_ratio(dy / height)))
    return pixels, None


def generate_leafy_grass(height, rng):
    pixels = []
    root_w = 1 if height < 8 else 2
    for rdx in range(-root_w // 2, root_w // 2 + 1):
        pixels.append((rdx, 0, 0))
        if height > 5:
            pixels.append((rdx, 1, 0))
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
    num_leaves = rng.randint(1, min(3, max(1, height // 4)))
    used_dy = set()
    leaf_lo = max(2, height // 3)
    for _ in range(num_leaves):
        if leaf_lo > height - 1:
            break  # 葉を付けられないほど低い草（height<=2）
        leaf_dy = rng.randint(leaf_lo, height - 1)
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
    return pixels, None


def generate_flower_grass(height, rng):
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
    num_leaves = rng.randint(0, min(2, max(0, height // 5)))
    used_dy = set()
    leaf_lo = max(2, height // 3)
    for _ in range(num_leaves):
        if leaf_lo > height - 2:
            break  # 葉を付けられないほど低い草
        leaf_dy = rng.randint(leaf_lo, height - 2)
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


# --- Layout generation ---
def generate_grass_data(config, screen_width):
    seed = config.get("seed", random.randint(0, 999999))
    rng = random.Random(seed)
    min_h = config.get("min_height", 4)
    max_h = config.get("max_height", 20)
    wind = config.get("wind", 50)
    palette_indices = config.get("palette_indices", [0])
    active_flowers = get_active_flower_colors(config) or FLOWER_COLORS
    slim_pct = config.get("slim_ratio", 40)
    flower_pct = config.get("flower_ratio", 15)
    total = slim_pct + flower_pct
    if total > 100:
        slim_pct = int(slim_pct / total * 100)
        flower_pct = 100 - slim_pct
    cluster_density = config.get("cluster_density", 70) / 100.0
    cluster_count = config.get("cluster_count", 40)
    num_clusters = config.get("num_clusters", 5)
    scatter_density = config.get("scatter_density", 20) / 100.0
    scatter_count = config.get("scatter_count", 20)
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
            flower_color = rng.choice(active_flowers)
        else:
            pixels, flower_color = generate_leafy_grass(height, rng)
        return {
            "x": cx, "pixels": pixels, "palette_idx": pal_idx,
            "flower_color": flower_color, "sway_base": sway_base,
            "max_dy": max((p[1] for p in pixels), default=1),
        }

    num_clusters = max(0, num_clusters)
    if num_clusters > 0 and cluster_count > 0:
        per_cluster = max(1, cluster_count // num_clusters)
        remainder = cluster_count - per_cluster * num_clusters
        margin = int(sparseness * 150)
        segment = max(1, (screen_width - margin) // num_clusters)
        cd = cluster_density
        cluster_placed = 0
        for ci in range(num_clusters):
            if cluster_placed >= cluster_count:
                break
            base_x = ci * segment + rng.randint(0, max(1, segment // 3))
            local_cd = max(0.05, min(1.0, cd + rng.uniform(-0.25, 0.25)))
            local_inner_min = max(3, int(15 * (1 - local_cd * 0.8)))
            local_inner_max = max(local_inner_min + 3, int(30 * (1 - local_cd * 0.7)))
            this_count = per_cluster + (1 if ci < remainder else 0)
            this_count = max(1, this_count + rng.randint(-2, 2))
            cx = base_x
            for _ in range(this_count):
                if cluster_placed >= cluster_count or cx >= screen_width:
                    break
                positions.append(make_one(cx))
                cluster_placed += 1
                cx += rng.randint(local_inner_min, local_inner_max)

    sd = scatter_density
    scatter_gap_min = max(10, int(40 * (1 - sd * 0.7)))
    scatter_gap_max = max(scatter_gap_min + 10, int(100 * (1 - sd * 0.5)))
    scatter_placed = 0
    sx = rng.randint(5, 40)
    while sx < screen_width and scatter_placed < scatter_count:
        positions.append(make_one(sx))
        scatter_placed += 1
        sx += rng.randint(scatter_gap_min, scatter_gap_max)

    positions.sort(key=lambda p: p["x"])
    return positions, seed


# --- GrassBlade ---
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

    def draw(self, painter, ground_y, alpha=255, tint=None, pixel_size=None, scale=None):
        s = scale or 1.0
        pw = pixel_size or PIXEL_SIZE
        ph = int(PIXEL_SIZE * s)       # height & spacing scaled
        md = max(self.max_dy, 1)
        for dx, dy, shade in self.pixels:
            sf = dy / md
            draw_x = int(self.base_x + (dx + self.sway * sf) * ph)
            draw_y = int(ground_y - (dy + 1) * ph)
            c = apply_tint(self.colors[shade], tint)
            c.setAlpha(alpha)
            painter.fillRect(draw_x, draw_y, pw, ph, c)
        if self.flower_color:
            for fx, fy in self.flower_pixels:
                sf = fy / md
                draw_x = int(self.base_x + (fx + self.sway * sf) * ph)
                draw_y = int(ground_y - (fy + 1) * ph)
                c = apply_tint(self.flower_color, tint)
                c.setAlpha(alpha)
                painter.fillRect(draw_x, draw_y, pw, ph, c)


# --- GrassScene ---
class GrassScene(BaseScene):
    BASE_WIDTH = 2400

    def __init__(self):
        self.grasses = []
        self.pixel_size = PIXEL_SIZE
        self.scale = 1.0

    def get_area_height(self, config):
        max_h = config.get("max_height", 20)
        s = config.get("grass_scale", 100) / 100.0
        return max(80, int(max_h * PIXEL_SIZE * s + 30))

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("grass_scale", 100) / 100.0
        self.pixel_size = config.get("grass_thickness", 4)
        palette_indices = config.get("palette_indices", [0])
        palettes = [PALETTE_PRESETS[i] for i in palette_indices if i < len(PALETTE_PRESETS)]
        if not palettes:
            palettes = [PALETTE_PRESETS[0]]
        ratio = screen_width / self.BASE_WIDTH
        scaled_config = config.copy()
        for key in ["cluster_count", "scatter_count", "num_clusters"]:
            if key in scaled_config:
                scaled_config[key] = max(1, round(scaled_config[key] * ratio))
        data_list, _ = generate_grass_data(scaled_config, widget_width)
        self.grasses = [GrassBlade(d, palettes) for d in data_list]
        # 左下のハンバーガーボタンのエリアを避ける（全体を右に詰める）
        avoid = hamburger_avoid_px(self.scale)
        if widget_width > avoid:
            for g in self.grasses:
                g.base_x = avoid + g.base_x * (widget_width - avoid) // widget_width

    def update(self, wind_sim, mouse_pos=None):
        for g in self.grasses:
            wave = wind_sim.get_wave_at(g.base_x)
            g.update(wave)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        s = self.scale
        for g in self.grasses:
            alpha = get_alpha(g.base_x) if get_alpha else 255
            g.draw(painter, ground_y, alpha, tint, int(self.pixel_size * s), s)


# ---------------------------------------------------------------------------
# プラグイン登録（設定タブ・gather・i18n は main.py から移設）
# ---------------------------------------------------------------------------

def _build_settings(dialog):
    """設定タブ（草・配置）を構築して [(widget, タブ名), ...] を返す"""
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QCheckBox,
    )
    from i18n import t

    # === タブ1: 草 ===
    tab_grass = QWidget()
    tgl = QVBoxLayout(tab_grass)

    g1 = QGroupBox(t("grass_length"))
    g1l = QVBoxLayout(g1)
    dialog.min_h_slider = dialog._add_slider(g1l, t("min"), 2, 15, dialog.config.get("min_height", 4))
    dialog.max_h_slider = dialog._add_slider(g1l, t("max"), 5, 30, dialog.config.get("max_height", 20))
    dialog.thickness_slider = dialog._add_slider(g1l, t("thickness"), 1, 12, dialog.config.get("grass_thickness", 4))
    tgl.addWidget(g1)

    dialog.grass_scale_slider = dialog._add_slider(g1l, t("display_scale"), 25, 200, dialog.config.get("grass_scale", 100))

    g_type = QGroupBox(t("grass_type"))
    g_type_l = QVBoxLayout(g_type)
    desc = QLabel(t("type_desc"))
    desc.setStyleSheet("color: #666; font-size: 11px;")
    g_type_l.addWidget(desc)
    dialog.slim_slider = dialog._add_slider(g_type_l, t("slim"), 0, 100, dialog.config.get("slim_ratio", 40))
    dialog.flower_slider = dialog._add_slider(g_type_l, t("flower"), 0, 100, dialog.config.get("flower_ratio", 15))
    dialog.balance_label = QLabel()
    dialog.balance_label.setStyleSheet("color: #444; font-size: 11px;")
    g_type_l.addWidget(dialog.balance_label)

    def update_balance_label():
        s = dialog.slim_slider.value()
        f = dialog.flower_slider.value()
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
        dialog.balance_label.setText(
            t("balance_fmt").format(s=s_pct, l=leafy, f=f_pct)
        )

    dialog.slim_slider.valueChanged.connect(update_balance_label)
    dialog.flower_slider.valueChanged.connect(update_balance_label)
    update_balance_label()
    tgl.addWidget(g_type)

    # 花の色
    g_fc = QGroupBox(t("flower_colors"))
    g_fcl = QVBoxLayout(g_fc)
    dialog.flower_color_checks = []
    enabled_flowers = dialog.config.get("flower_colors_enabled", list(range(len(FLOWER_COLORS_ALL))))
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
        dialog.flower_color_checks.append(cb)
    tgl.addWidget(g_fc)

    # === タブ2: 配置 ===
    tab_layout = QWidget()
    tll = QVBoxLayout(tab_layout)

    gc = QGroupBox(t("cluster_area"))
    gcl = QVBoxLayout(gc)
    dialog.num_clusters_slider = dialog._add_slider(gcl, t("num_clusters"), 0, 20, dialog.config.get("num_clusters", 5))
    dialog.cluster_count_slider = dialog._add_slider(gcl, t("total_count"), 0, 150, dialog.config.get("cluster_count", 40))
    dialog.cluster_density_slider = dialog._add_slider(gcl, t("density"), 0, 100, dialog.config.get("cluster_density", 70))
    dialog.sparseness_slider = dialog._add_slider(gcl, t("spacing"), 0, 100, dialog.config.get("sparseness", 50))
    cd_desc = QLabel(t("cluster_desc"))
    cd_desc.setStyleSheet("color: #666; font-size: 10px;")
    gcl.addWidget(cd_desc)
    tll.addWidget(gc)

    gs = QGroupBox(t("scatter_area"))
    gsl = QVBoxLayout(gs)
    dialog.scatter_count_slider = dialog._add_slider(gsl, t("count"), 0, 150, dialog.config.get("scatter_count", 20))
    dialog.scatter_density_slider = dialog._add_slider(gsl, t("scatter_density"), 0, 100, dialog.config.get("scatter_density", 20))
    sd_desc = QLabel(t("scatter_desc"))
    sd_desc.setStyleSheet("color: #666; font-size: 10px;")
    gsl.addWidget(sd_desc)
    tll.addWidget(gs)

    return [(tab_grass, t("tab_grass")), (tab_layout, t("tab_layout"))]


def _gather(dialog):
    """設定タブの現在値を config 辞書で返す"""
    return {
        "min_height": dialog.min_h_slider.value(),
        "max_height": max(dialog.max_h_slider.value(), dialog.min_h_slider.value() + 1),
        "grass_thickness": dialog.thickness_slider.value(),
        "grass_scale": dialog.grass_scale_slider.value(),
        "num_clusters": dialog.num_clusters_slider.value(),
        "cluster_count": dialog.cluster_count_slider.value(),
        "cluster_density": dialog.cluster_density_slider.value(),
        "sparseness": dialog.sparseness_slider.value(),
        "scatter_count": dialog.scatter_count_slider.value(),
        "scatter_density": dialog.scatter_density_slider.value(),
        "slim_ratio": dialog.slim_slider.value(),
        "flower_ratio": dialog.flower_slider.value(),
        "palette_indices": dialog.config.get("palette_indices", [0]),
        "flower_colors_enabled": [i for i, btn in enumerate(dialog.flower_color_checks) if btn.isChecked()],
    }


SCENE = {
    "key": "grass",
    "label_key": "scene_grass",
    "class": GrassScene,
    "order": 10,
    "scale_key": "grass_scale",
    "preset_keys": [
        "min_height", "max_height", "grass_thickness", "num_clusters", "cluster_count",
        "cluster_density", "sparseness", "scatter_count", "scatter_density",
        "slim_ratio", "flower_ratio", "palette_indices", "flower_colors_enabled", "seed",
    ],
    "preset_label_key": "grass_preset",
    "texts": {
        "ja": {
            "scene_grass": "草原",
            "tab_grass": "草",
            "tab_layout": "配置",
            "type_desc": "しゅっとした草 / 葉付き草 / 花付き草 の比率",
            "balance_fmt": "  → 細い草 {s}% : 葉付き {l}% : 花 {f}%",
            "flower_colors": "花の色",
            "fc_red": "赤",
            "fc_vermilion": "朱色",
            "fc_blue": "青",
            "fc_lightblue": "水色",
            "fc_yellow": "黄色",
            "fc_pink": "ピンク",
            "fc_purple": "紫",
            "fc_white": "白",
            "cluster_desc": "塊の数x密集度=茂みの見た目 / 間隔=塊どうしの距離",
            "scatter_desc": "画面全体にまばらに生える草",
            "grass_preset": "草原プリセット",
            "save_grass": "草を保存",
        },
        "en": {
            "scene_grass": "Grassland",
            "tab_grass": "Grass",
            "tab_layout": "Layout",
            "type_desc": "Ratio of slim / leafy / flowering grass",
            "balance_fmt": "  → Slim {s}% : Leafy {l}% : Flower {f}%",
            "flower_colors": "Flower Colors",
            "fc_red": "Red",
            "fc_vermilion": "Vermilion",
            "fc_blue": "Blue",
            "fc_lightblue": "Light Blue",
            "fc_yellow": "Yellow",
            "fc_pink": "Pink",
            "fc_purple": "Purple",
            "fc_white": "White",
            "cluster_desc": "Clusters x Density = Bush look / Spacing = Distance between",
            "scatter_desc": "Grass scattered across the entire screen",
            "grass_preset": "Grassland Preset",
            "save_grass": "Save Grass",
        },
    },
    "build_settings": _build_settings,
    "gather": _gather,
}
