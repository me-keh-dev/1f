"""Aquarium scene - water plants swaying with goldfish swimming (water physics)"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtGui import QColor, QLinearGradient

# --- Water plant palettes ---
PLANT_PALETTES = [
    {"dark": (0x0a, 0x3a, 0x2a), "mid": (0x15, 0x5a, 0x40),
     "bright": (0x20, 0x80, 0x58), "tip": (0x40, 0xb0, 0x78)},
    {"dark": (0x0a, 0x3a, 0x3a), "mid": (0x15, 0x55, 0x55),
     "bright": (0x28, 0x80, 0x78), "tip": (0x50, 0xa8, 0x98)},
    {"dark": (0x10, 0x40, 0x20), "mid": (0x20, 0x65, 0x35),
     "bright": (0x35, 0x90, 0x50), "tip": (0x55, 0xc0, 0x70)},
]

# --- Goldfish shape (cute, with flowing frill tail) ---
GOLDFISH_SHAPE = [
    # Dorsal fin
    (-1, -3, 'fin'), (0, -3, 'fin'),
    # Body top
    (-2, -2, 'body'), (-1, -2, 'body'), (0, -2, 'body'), (1, -2, 'body'), (2, -2, 'body'),
    # Body upper + tail base
    (-3, -1, 'tail'),
    (-2, -1, 'body'), (-1, -1, 'body'), (0, -1, 'body'), (1, -1, 'body'), (2, -1, 'body'),
    # Body lower + tail base
    (-3, 0, 'tail'),
    (-2, 0, 'body'), (-1, 0, 'body'), (0, 0, 'body'), (1, 0, 'body'), (2, 0, 'body'),
    # Belly
    (-2, 1, 'belly'), (-1, 1, 'belly'), (0, 1, 'belly'), (1, 1, 'belly'),
    # Ventral fin
    (0, 2, 'fin'),
    # Tail frill (connected, draping downward)
    (-4, -1, 'tail'), (-4, 0, 'tail'), (-4, 1, 'tail'),
    (-5, -1, 'tail'), (-5, 0, 'tail'), (-5, 1, 'tail'), (-5, 2, 'tail'),
    (-6, -1, 'tail'), (-6, 0, 'tail'), (-6, 1, 'tail'), (-6, 2, 'tail'),
    (-7, 0, 'tail'), (-7, 1, 'tail'), (-7, 2, 'tail'),
    # Cheek
    (2, 0, 'cheek'),
    # Eye (overwrites body)
    (2, -2, 'eye'),
    # Eye highlight
    (2, -1, 'highlight'),
]

GOLDFISH_VARIANTS = [
    {'body': (220, 30, 25), 'tail': (185, 20, 15), 'fin': (240, 55, 45),
     'belly': (245, 90, 80), 'eye': (25, 25, 30), 'cheek': (255, 80, 90),
     'highlight': (255, 235, 230)},
]


# --- Water plant with water physics ---
class WaterPlant:
    def __init__(self, base_x, pixels, palette, sway_base, max_dy):
        self.base_x = base_x
        self.pixels = pixels
        self.colors = [
            QColor(*palette["dark"]), QColor(*palette["mid"]),
            QColor(*palette["bright"]), QColor(*palette["tip"]),
        ]
        self.noise_gen = PinkNoiseGenerator()
        self.sway = 0.0
        self.sway_vel = 0.0
        self.sway_base = sway_base
        self.max_dy = max(max_dy, 1)

    def update(self, wind_wave):
        local = self.noise_gen.next()
        target = (wind_wave * 0.35 + local * 0.25) * self.sway_base
        # Water physics: spring force + drag
        force = (target - self.sway) * 0.008
        self.sway_vel += force
        self.sway_vel *= 0.92  # water drag
        self.sway += self.sway_vel

    def draw(self, painter, ground_y, alpha=255, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        md = self.max_dy
        for dx, dy, shade in self.pixels:
            sf = dy / md
            draw_x = int(self.base_x + (dx + self.sway * sf) * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = apply_tint(self.colors[shade], tint)
            # Height-based transparency: tips are softer
            tip_fade = max(0.35, 1.0 - sf * 0.6)
            pixel_alpha = int(alpha * tip_fade)
            c.setAlpha(pixel_alpha)
            painter.fillRect(draw_x, draw_y, ps, ps, c)
            # Soft glow around edges (semi-transparent halo)
            glow = QColor(c.red(), c.green(), c.blue(), int(pixel_alpha * 0.25))
            painter.fillRect(draw_x - 1, draw_y, ps + 2, ps, glow)
            painter.fillRect(draw_x, draw_y - 1, ps, ps + 2, glow)


# --- Fish with water physics ---
class Fish:
    def __init__(self, x, y, shape, colors, direction, speed, min_y, max_y):
        self.x = float(x)
        self.y = float(y)
        self.shape = shape
        self.colors = {k: QColor(*v) for k, v in colors.items()}
        self.speed = speed
        self.min_y = min_y
        self.max_y = max_y
        # Water physics: velocity-based movement
        self.vx = speed * direction
        self.vy = 0.0
        self.direction = direction       # visual direction (discrete: -1 or 1)
        self.target_dir = direction      # intended direction
        self.drag = 0.02                 # water resistance
        self.accel = 0.012               # gentle thrust
        # Swim animation
        self.swim_phase = random.uniform(0, math.pi * 2)
        # Tail physics: independent sway with lag
        self.tail_sway = 0.0
        self.tail_vel = 0.0
        # 1/f noise for natural movement
        self.noise_x = PinkNoiseGenerator()
        self.noise_y = PinkNoiseGenerator()
        # AI
        self.think_counter = random.randint(60, 240)
        self.target_vy_force = 0.0

    def update(self, screen_width):
        self.swim_phase += abs(self.vx) * 0.2 + 0.02
        # Think
        self.think_counter -= 1
        if self.think_counter <= 0:
            self.think_counter = random.randint(90, 300)
            if random.random() < 0.15:
                self.target_dir *= -1
            self.target_vy_force = random.uniform(-0.008, 0.008)
            self.speed = self.speed * random.uniform(0.8, 1.2)
        # 1/f noise adds natural fluctuation to thrust
        nx = self.noise_x.next() * self.speed * 0.15
        ny = self.noise_y.next() * self.speed * 0.08
        # Apply thrust toward target direction (gentle acceleration)
        target_vx = self.speed * self.target_dir
        self.vx += (target_vx - self.vx) * self.accel + nx * 0.01
        # Water drag
        self.vx *= (1 - self.drag)
        self.vy += self.target_vy_force + ny * 0.005
        self.vy *= (1 - self.drag * 1.5)
        # Flip visual direction when velocity crosses threshold
        if self.vx > 0.03:
            self.direction = 1
        elif self.vx < -0.03:
            self.direction = -1
        # Move
        self.x += self.vx
        self.y += self.vy
        # Vertical bounds (soft bounce)
        if self.y < self.min_y:
            self.y = self.min_y
            self.vy = abs(self.vy) * 0.3
            self.target_vy_force = abs(self.target_vy_force)
        elif self.y > self.max_y:
            self.y = self.max_y
            self.vy = -abs(self.vy) * 0.3
            self.target_vy_force = -abs(self.target_vy_force)
        # Wrap at edges
        margin = 60
        if self.x > screen_width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = screen_width + margin
        # Tail physics: follows body with spring + drag (creates flutter)
        speed_ratio = min(1.0, abs(self.vx) / max(self.speed, 0.1))
        # Tail target: natural sine wag + extra flutter when slow (turning)
        tail_target = math.sin(self.swim_phase) * 0.4
        turn_flutter = (1.0 - speed_ratio) * math.sin(self.swim_phase * 1.5) * 0.8
        tail_target += turn_flutter
        tail_force = (tail_target - self.tail_sway) * 0.06
        self.tail_vel += tail_force
        self.tail_vel *= 0.85  # tail drag
        self.tail_sway += self.tail_vel

    def draw(self, painter, alpha=255, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        flutter = self.tail_sway * 0.35 * (-self.direction)
        # Layer 1: static tail (fills base, no gaps)
        for dx, dy, part in self.shape:
            if part != 'tail':
                continue
            sx = int(self.x + dx * self.direction * ps)
            sy = int(self.y + dy * ps)
            c = self.colors.get(part)
            if c is None:
                continue
            c = apply_tint(c, tint) if tint else QColor(c)
            c.setAlpha(alpha)
            painter.fillRect(sx, sy, ps, ps, c)
            # Soft glow
            glow = QColor(c.red(), c.green(), c.blue(), int(alpha * 0.2))
            painter.fillRect(sx - 1, sy, ps + 2, ps, glow)
            painter.fillRect(sx, sy - 1, ps, ps + 2, glow)
        # Layer 2: fluttering tail (tips move more, base stays)
        for dx, dy, part in self.shape:
            if part != 'tail':
                continue
            dist = max(0, abs(dx) - 3)
            dist_factor = dist / 4.0
            sx = int(self.x + (dx * self.direction + flutter * dist_factor) * ps)
            sy = int(self.y + dy * ps)
            c = self.colors.get(part)
            if c is None:
                continue
            c = apply_tint(c, tint) if tint else QColor(c)
            # Tip fade: further from body = more transparent
            tail_alpha = int(alpha * max(0.4, 1.0 - dist_factor * 0.5))
            c.setAlpha(tail_alpha)
            painter.fillRect(sx, sy, ps, ps, c)
            glow = QColor(c.red(), c.green(), c.blue(), int(tail_alpha * 0.25))
            painter.fillRect(sx - 1, sy, ps + 2, ps, glow)
            painter.fillRect(sx, sy - 1, ps, ps + 2, glow)
        # Body, fins, etc.
        for dx, dy, part in self.shape:
            if part == 'tail':
                continue
            actual_dx = dx * self.direction
            body_wave = 0
            if part in ('body', 'belly', 'fin'):
                body_wave = math.sin(self.swim_phase + dx * 0.3) * 0.05
            sx = int(self.x + actual_dx * ps)
            sy = int(self.y + (dy + body_wave) * ps)
            c = self.colors.get(part)
            if c is None:
                continue
            c = apply_tint(c, tint) if tint else QColor(c)
            c.setAlpha(alpha)
            painter.fillRect(sx, sy, ps, ps, c)
            # Soft glow on body
            if part in ('body', 'belly', 'fin', 'cheek'):
                glow = QColor(c.red(), c.green(), c.blue(), int(alpha * 0.2))
                painter.fillRect(sx - 1, sy, ps + 2, ps, glow)
                painter.fillRect(sx, sy - 1, ps, ps + 2, glow)


# --- Bubble ---
class Bubble:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vy = -random.uniform(0.3, 0.8)
        self.vx = 0.0
        self.size = random.choice([1, 1, 2])
        self.alpha = random.randint(120, 200)
        self.alive = True

    def update(self):
        # Buoyancy + drag
        self.vy *= 0.98
        self.vx += random.uniform(-0.02, 0.02)
        self.vx *= 0.95
        self.y += self.vy
        self.x += self.vx
        self.alpha -= 1
        if self.alpha <= 0:
            self.alive = False

    def draw(self, painter):
        if not self.alive:
            return
        ps = PIXEL_SIZE
        c = QColor(180, 220, 255, self.alpha)
        s = ps * self.size
        painter.fillRect(int(self.x), int(self.y), s, s, c)


# --- Water plant generation ---
def _shade_for_ratio(ratio):
    if ratio < 0.3:
        return 0
    elif ratio < 0.55:
        return 1
    elif ratio < 0.8:
        return 2
    return 3


def _generate_water_plant(height, rng):
    pixels = []
    pixels.append((0, 0, 0))
    if height > 4:
        pixels.append((0, 1, 0))
    curve_dir = rng.choice([-1, 1])
    curve_strength = rng.uniform(0.15, 0.45)
    cx = 0.0
    start = 1 if height <= 4 else 2
    for dy in range(start, height):
        cx += curve_dir * curve_strength * (dy / height)
        if rng.random() < 0.12:
            curve_dir *= -1
        dx = round(cx)
        pixels.append((dx, dy, _shade_for_ratio(dy / height)))
    num_leaves = rng.randint(1, min(4, max(1, height // 3)))
    used_dy = set()
    for _ in range(num_leaves):
        leaf_dy = rng.randint(max(2, height // 4), height - 1)
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
            ly = leaf_dy + (0 if rng.random() < 0.6 else rng.choice([-1, 1]))
            ly = max(0, ly)
            shade = 3 if (ly / height) > 0.5 else 2
            pixels.append((lx, ly, shade))
    max_dy = max((p[1] for p in pixels), default=1)
    return pixels, max_dy


# --- AquariumScene ---
class AquariumScene(BaseScene):
    BASE_WIDTH = 2400

    def __init__(self):
        self.plants = []
        self.fish_list = []
        self.bubbles = []
        self.bubble_timer = 0
        self.widget_width = 0
        self.area_height = 200
        self.scale = 1.0

    def get_area_height(self, config):
        s = config.get("aq_scale", 100) / 100.0
        return int(200 * s)

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("aq_scale", 100) / 100.0
        self.ps = max(1, int(PIXEL_SIZE * self.scale))
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed)
        wind = config.get("wind", 50)
        self._generate_plants(rng, widget_width, wind, config)
        # 左下のハンバーガーボタンのエリアを避ける（水草を右に詰める）
        avoid = hamburger_avoid_px(self.scale)
        if widget_width > avoid:
            for p in self.plants:
                p.base_x = avoid + p.base_x * (widget_width - avoid) // widget_width
        self._generate_fish(rng, widget_width, config)
        self.bubbles = []

    def _generate_plants(self, rng, width, wind, config):
        self.plants = []
        min_h = config.get("aq_plant_min_height", 8)
        max_h = config.get("aq_plant_max_height", 30)
        cluster_count = config.get("aq_cluster_count", 3)
        cluster_size = config.get("aq_cluster_size", 8)
        cluster_density = config.get("aq_cluster_density", 70) / 100.0
        scatter_count = config.get("aq_scatter_count", 15)
        scatter_density = config.get("aq_scatter_density", 30) / 100.0

        def place_one(cx):
            height = rng.randint(min_h, max_h)
            palette = rng.choice(PLANT_PALETTES)
            sway_base = rng.uniform(2.5, 6.0) * (wind / 50)
            pixels, max_dy = _generate_water_plant(height, rng)
            self.plants.append(WaterPlant(cx, pixels, palette, sway_base, max_dy))

        # Cluster placement
        if cluster_count > 0 and cluster_size > 0:
            segment = max(1, width // max(1, cluster_count))
            cd_gap_min = max(3, int(15 * (1 - cluster_density * 0.8)))
            cd_gap_max = max(cd_gap_min + 3, int(30 * (1 - cluster_density * 0.7)))
            for ci in range(cluster_count):
                base_x = ci * segment + rng.randint(0, max(1, segment // 3))
                cx = base_x
                for _ in range(cluster_size):
                    if cx >= width:
                        break
                    place_one(cx)
                    cx += rng.randint(cd_gap_min, cd_gap_max)

        # Scatter placement
        sd_gap_min = max(10, int(50 * (1 - scatter_density * 0.7)))
        sd_gap_max = max(sd_gap_min + 10, int(120 * (1 - scatter_density * 0.5)))
        sx = rng.randint(5, 30)
        placed = 0
        while sx < width and placed < scatter_count:
            place_one(sx)
            placed += 1
            sx += rng.randint(sd_gap_min, sd_gap_max)

    def _generate_fish(self, rng, width, config):
        self.fish_list = []
        ground_y = self.area_height
        y_top = config.get("aq_fish_y_top", 10) / 100.0
        y_bottom = config.get("aq_fish_y_bottom", 55) / 100.0
        fish_min_y = int(ground_y * y_top)
        fish_max_y = int(ground_y * max(y_top + 0.05, y_bottom))
        fish_count = config.get("aq_fish_count", 6)
        for _ in range(fish_count):
            x = rng.randint(0, width)
            y = rng.randint(fish_min_y, fish_max_y)
            colors = rng.choice(GOLDFISH_VARIANTS)
            direction = rng.choice([-1, 1])
            speed_min = config.get("aq_fish_speed_min", 30) / 100.0
            speed_max = config.get("aq_fish_speed_max", 65) / 100.0
            speed = rng.uniform(speed_min, max(speed_min + 0.05, speed_max))
            self.fish_list.append(
                Fish(x, y, GOLDFISH_SHAPE, colors, direction, speed, fish_min_y, fish_max_y))

    def _update_bubbles(self):
        self.bubble_timer += 1
        if self.bubble_timer % 20 == 0 and self.plants:
            plant = random.choice(self.plants)
            if plant.pixels:
                top = max(plant.pixels, key=lambda p: p[1])
                bx = plant.base_x + top[0] * PIXEL_SIZE
                by = self.area_height - (top[1] + 1) * PIXEL_SIZE
                self.bubbles.append(Bubble(bx, by))
        for b in self.bubbles:
            b.update()
        self.bubbles = [b for b in self.bubbles if b.alive and b.y > -10]
        if len(self.bubbles) > 50:
            self.bubbles = self.bubbles[-50:]

    def update(self, wind_sim, mouse_pos=None):
        for p in self.plants:
            wave = wind_sim.get_wave_at(p.base_x)
            p.update(wave)
        for f in self.fish_list:
            f.update(self.widget_width)
        self._update_bubbles()

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        gradient = QLinearGradient(0, 0, 0, ground_y)
        gradient.setColorAt(0.0, QColor(15, 50, 100, 0))
        gradient.setColorAt(0.5, QColor(15, 50, 100, 25))
        gradient.setColorAt(1.0, QColor(10, 35, 70, 50))
        painter.fillRect(0, 0, self.widget_width, ground_y, gradient)
        ps = self.ps
        sand = QColor(194, 178, 128, 140)
        painter.fillRect(0, ground_y - 2 * ps, self.widget_width, 2 * ps, sand)
        for p in self.plants:
            alpha = get_alpha(p.base_x) if get_alpha else 255
            p.draw(painter, ground_y, alpha, tint, ps)
        for f in self.fish_list:
            alpha = get_alpha(int(f.x)) if get_alpha else 255
            f.draw(painter, alpha, tint, ps)
        for b in self.bubbles:
            b.draw(painter)


# ---------------------------------------------------------------------------
# プラグイン登録（設定タブ・gather・i18n は main.py から移設）
# ---------------------------------------------------------------------------

def _build_settings(dialog):
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QGroupBox, QScrollArea,
    )
    from i18n import t

    tab_aq = QWidget()
    aq_scroll = QScrollArea()
    aq_scroll.setWidgetResizable(True)
    aq_inner = QWidget()
    aq_layout = QVBoxLayout(aq_inner)

    dialog.aq_scale_slider = dialog._add_slider(aq_layout, t("display_scale"), 25, 200, dialog.config.get("aq_scale", 100))

    g_aq_plant = QGroupBox(t("aq_plant_length"))
    g_apl = QVBoxLayout(g_aq_plant)
    dialog.aq_min_h_slider = dialog._add_slider(g_apl, t("min"), 2, 20, dialog.config.get("aq_plant_min_height", 8))
    dialog.aq_max_h_slider = dialog._add_slider(g_apl, t("max"), 5, 40, dialog.config.get("aq_plant_max_height", 30))
    aq_layout.addWidget(g_aq_plant)

    g_aq_cluster = QGroupBox(t("aq_cluster"))
    g_acl = QVBoxLayout(g_aq_cluster)
    dialog.aq_cluster_count_slider = dialog._add_slider(g_acl, t("num_clusters"), 0, 10, dialog.config.get("aq_cluster_count", 3))
    dialog.aq_cluster_size_slider = dialog._add_slider(g_acl, t("total_count"), 1, 20, dialog.config.get("aq_cluster_size", 8))
    dialog.aq_cluster_density_slider = dialog._add_slider(g_acl, t("density"), 0, 100, dialog.config.get("aq_cluster_density", 70))
    aq_layout.addWidget(g_aq_cluster)

    g_aq_scatter = QGroupBox(t("aq_scatter"))
    g_asl = QVBoxLayout(g_aq_scatter)
    dialog.aq_scatter_count_slider = dialog._add_slider(g_asl, t("count"), 0, 50, dialog.config.get("aq_scatter_count", 15))
    dialog.aq_scatter_density_slider = dialog._add_slider(g_asl, t("scatter_density"), 0, 100, dialog.config.get("aq_scatter_density", 30))
    aq_layout.addWidget(g_aq_scatter)

    g_aq_fish = QGroupBox(t("aq_fish_settings"))
    g_afl = QVBoxLayout(g_aq_fish)
    dialog.aq_fish_count_slider = dialog._add_slider(g_afl, t("aq_fish_count"), 1, 20, dialog.config.get("aq_fish_count", 6))
    dialog.aq_speed_min_slider = dialog._add_slider(g_afl, t("aq_speed_min"), 5, 100, dialog.config.get("aq_fish_speed_min", 30))
    dialog.aq_speed_max_slider = dialog._add_slider(g_afl, t("aq_speed_max"), 5, 100, dialog.config.get("aq_fish_speed_max", 65))
    dialog.aq_fish_y_top_slider = dialog._add_slider(g_afl, t("aq_y_top"), 0, 80, dialog.config.get("aq_fish_y_top", 10))
    dialog.aq_fish_y_bottom_slider = dialog._add_slider(g_afl, t("aq_y_bottom"), 20, 90, dialog.config.get("aq_fish_y_bottom", 55))
    aq_layout.addWidget(g_aq_fish)

    aq_layout.addStretch()
    aq_scroll.setWidget(aq_inner)
    tab_aq_layout = QVBoxLayout(tab_aq)
    tab_aq_layout.setContentsMargins(0, 0, 0, 0)
    tab_aq_layout.addWidget(aq_scroll)

    return [(tab_aq, t("aq_settings"))]


def _gather(dialog):
    return {
        "aq_plant_min_height": dialog.aq_min_h_slider.value(),
        "aq_plant_max_height": dialog.aq_max_h_slider.value(),
        "aq_cluster_count": dialog.aq_cluster_count_slider.value(),
        "aq_cluster_size": dialog.aq_cluster_size_slider.value(),
        "aq_cluster_density": dialog.aq_cluster_density_slider.value(),
        "aq_scatter_count": dialog.aq_scatter_count_slider.value(),
        "aq_scatter_density": dialog.aq_scatter_density_slider.value(),
        "aq_fish_count": dialog.aq_fish_count_slider.value(),
        "aq_fish_speed_min": dialog.aq_speed_min_slider.value(),
        "aq_fish_speed_max": dialog.aq_speed_max_slider.value(),
        "aq_scale": dialog.aq_scale_slider.value(),
        "aq_fish_y_top": dialog.aq_fish_y_top_slider.value(),
        "aq_fish_y_bottom": dialog.aq_fish_y_bottom_slider.value(),
    }


SCENE = {
    "key": "aquarium",
    "label_key": "scene_aquarium",
    "class": AquariumScene,
    "order": 20,
    "scale_key": "aq_scale",
    "preset_keys": [
        "aq_plant_min_height", "aq_plant_max_height",
        "aq_cluster_count", "aq_cluster_size", "aq_cluster_density",
        "aq_scatter_count", "aq_scatter_density",
        "aq_fish_count", "aq_fish_speed_min", "aq_fish_speed_max",
        "aq_fish_y_top", "aq_fish_y_bottom", "seed",
    ],
    "preset_label_key": "aq_preset",
    "texts": {
        "ja": {
            "scene_aquarium": "アクアリウム（水草＋金魚）",
            "aq_settings": "アクアリウム設定",
            "aq_plant_length": "水草の長さ",
            "aq_cluster": "密集エリア",
            "aq_scatter": "散在エリア",
            "aq_fish_settings": "金魚",
            "aq_fish_count": "数",
            "aq_speed_min": "速度 最低",
            "aq_speed_max": "速度 最高",
            "aq_y_top": "上限位置",
            "aq_y_bottom": "下限位置",
            "aq_preset": "アクアリウムプリセット",
        },
        "en": {
            "scene_aquarium": "Aquarium (Water Plants + Goldfish)",
            "aq_settings": "Aquarium Settings",
            "aq_plant_length": "Plant Length",
            "aq_cluster": "Cluster Area",
            "aq_scatter": "Scatter Area",
            "aq_fish_settings": "Goldfish",
            "aq_fish_count": "Count",
            "aq_speed_min": "Speed Min",
            "aq_speed_max": "Speed Max",
            "aq_y_top": "Top Pos",
            "aq_y_bottom": "Bottom Pos",
            "aq_preset": "Aquarium Preset",
        },
    },
    "build_settings": _build_settings,
    "gather": _gather,
}
