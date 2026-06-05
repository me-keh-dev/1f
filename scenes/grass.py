"""Grass scene - the original 1/f Yuragi grassland"""
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint
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

    def draw(self, painter, ground_y, alpha=255, tint=None, pixel_size=None):
        pw = pixel_size or PIXEL_SIZE  # width (thickness)
        ph = PIXEL_SIZE                # height & spacing (fixed)
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

    def get_area_height(self, config):
        max_h = config.get("max_height", 20)
        return max(80, max_h * PIXEL_SIZE + 30)

    def rebuild(self, config, screen_width, widget_width):
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

    def update(self, wind_sim):
        for g in self.grasses:
            wave = wind_sim.get_wave_at(g.base_x)
            g.update(wave)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        for g in self.grasses:
            alpha = get_alpha(g.base_x) if get_alpha else 255
            g.draw(painter, ground_y, alpha, tint, self.pixel_size)
