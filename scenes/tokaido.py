"""Tokaido scene - Edo-period pine-lined road with travelers"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint
from PyQt5.QtGui import QColor, QLinearGradient


# --- Pine tree colors ---
TRUNK_COLORS = {
    'trunk':      (101, 67, 33),
    'trunk_dark': (75, 50, 25),
}
CANOPY_COLORS = {
    'canopy_dark':   (20, 60, 28),
    'canopy':        (32, 88, 38),
    'canopy_bright': (48, 115, 55),
    'canopy_tip':    (65, 135, 65),
}

# --- Traveler shapes (2 walk frames each) ---
# (dx, dy, part) relative to feet position. dy negative = up.

# Generic traveler (旅人) - straw hat, simple clothing
TRAVELER_FRAMES = [
    [   # Frame 0 - left leg forward
        (0, -7, 'hat'), (1, -7, 'hat'),
        (-1, -6, 'hat'), (0, -6, 'head'), (1, -6, 'hat'),
        (0, -5, 'head'),
        (0, -4, 'body'), (-1, -4, 'body'),
        (0, -3, 'body'), (-1, -3, 'body'), (1, -3, 'arm'),
        (0, -2, 'body'),
        (0, -1, 'legs'), (1, -1, 'legs'),
        (-1, 0, 'legs'),
    ],
    [   # Frame 1 - right leg forward
        (0, -7, 'hat'), (1, -7, 'hat'),
        (-1, -6, 'hat'), (0, -6, 'head'), (1, -6, 'hat'),
        (0, -5, 'head'),
        (0, -4, 'body'), (-1, -4, 'body'),
        (0, -3, 'body'), (-1, -3, 'body'), (1, -3, 'arm'),
        (0, -2, 'body'),
        (-1, -1, 'legs'), (0, -1, 'legs'),
        (1, 0, 'legs'),
    ],
]

# 飛脚 (courier/runner) - headband, running pose
HIKYAKU_FRAMES = [
    [   # Frame 0
        (0, -6, 'headband'), (1, -6, 'headband'),
        (0, -5, 'head'), (1, -5, 'head'),
        (0, -4, 'body'),
        (-1, -3, 'body'), (0, -3, 'body'), (1, -3, 'arm'),
        (0, -2, 'body'),
        (1, -1, 'legs'),
        (-1, 0, 'legs'),
    ],
    [   # Frame 1
        (0, -6, 'headband'), (1, -6, 'headband'),
        (0, -5, 'head'), (1, -5, 'head'),
        (0, -4, 'body'),
        (-1, -3, 'body'), (0, -3, 'body'), (1, -3, 'arm'),
        (0, -2, 'body'),
        (-1, -1, 'legs'),
        (1, 0, 'legs'),
    ],
]

# 商人 (merchant) - carrying bundle
MERCHANT_FRAMES = [
    [   # Frame 0
        (1, -8, 'bundle'), (2, -8, 'bundle'),
        (1, -7, 'bundle'), (2, -7, 'bundle'),
        (0, -6, 'hat'),
        (-1, -5, 'hat'), (0, -5, 'head'), (1, -5, 'hat'),
        (0, -4, 'body'), (-1, -4, 'body'),
        (0, -3, 'body'), (-1, -3, 'body'),
        (0, -2, 'body'),
        (0, -1, 'legs'),
        (-1, 0, 'legs'),
    ],
    [   # Frame 1
        (1, -8, 'bundle'), (2, -8, 'bundle'),
        (1, -7, 'bundle'), (2, -7, 'bundle'),
        (0, -6, 'hat'),
        (-1, -5, 'hat'), (0, -5, 'head'), (1, -5, 'hat'),
        (0, -4, 'body'), (-1, -4, 'body'),
        (0, -3, 'body'), (-1, -3, 'body'),
        (0, -2, 'body'),
        (-1, -1, 'legs'),
        (0, 0, 'legs'),
    ],
]

# 侍 (samurai) - formal, with sword
SAMURAI_FRAMES = [
    [   # Frame 0
        (0, -7, 'hat'), (1, -7, 'hat'),
        (-1, -6, 'hat'), (0, -6, 'head'), (1, -6, 'hat'), (2, -6, 'hat'),
        (0, -5, 'head'),
        (-1, -4, 'body'), (0, -4, 'body'), (1, -4, 'body'),
        (-1, -3, 'body'), (0, -3, 'body'), (1, -3, 'body'),
        (-1, -2, 'body'), (0, -2, 'body'),
        (-2, -3, 'sword'), (-2, -2, 'sword'), (-2, -1, 'sword'),
        (0, -1, 'legs'),
        (-1, 0, 'legs'),
    ],
    [   # Frame 1
        (0, -7, 'hat'), (1, -7, 'hat'),
        (-1, -6, 'hat'), (0, -6, 'head'), (1, -6, 'hat'), (2, -6, 'hat'),
        (0, -5, 'head'),
        (-1, -4, 'body'), (0, -4, 'body'), (1, -4, 'body'),
        (-1, -3, 'body'), (0, -3, 'body'), (1, -3, 'body'),
        (-1, -2, 'body'), (0, -2, 'body'),
        (-2, -3, 'sword'), (-2, -2, 'sword'), (-2, -1, 'sword'),
        (-1, -1, 'legs'),
        (0, 0, 'legs'),
    ],
]

# Traveler type definitions: (frames, color_dict)
TRAVELER_TYPES = [
    {
        'name': 'traveler', 'frames': TRAVELER_FRAMES,
        'colors': {'hat': (180, 160, 100), 'head': (220, 190, 150), 'body': (80, 90, 130),
                   'arm': (70, 80, 120), 'legs': (100, 80, 50)},
    },
    {
        'name': 'traveler2', 'frames': TRAVELER_FRAMES,
        'colors': {'hat': (160, 140, 90), 'head': (215, 185, 145), 'body': (130, 90, 60),
                   'arm': (120, 80, 50), 'legs': (90, 70, 45)},
    },
    {
        'name': 'hikyaku', 'frames': HIKYAKU_FRAMES,
        'colors': {'headband': (200, 50, 40), 'head': (220, 190, 150), 'body': (240, 230, 210),
                   'arm': (230, 220, 200), 'legs': (100, 80, 50)},
    },
    {
        'name': 'merchant', 'frames': MERCHANT_FRAMES,
        'colors': {'hat': (170, 150, 100), 'head': (215, 185, 145), 'body': (60, 70, 90),
                   'bundle': (160, 120, 60), 'legs': (90, 70, 45)},
    },
    {
        'name': 'samurai', 'frames': SAMURAI_FRAMES,
        'colors': {'hat': (40, 40, 40), 'head': (220, 190, 150), 'body': (50, 50, 70),
                   'sword': (160, 160, 170), 'legs': (50, 45, 40)},
    },
]


# --- Pine tree ---
class PineTree:
    def __init__(self, base_x, pixels, trunk_h, max_dy, sway_base):
        self.base_x = base_x
        self.pixels = pixels
        self.trunk_h = trunk_h
        self.max_dy = max(max_dy, 1)
        self.sway_base = sway_base
        self.sway = 0.0
        self.noise_gen = PinkNoiseGenerator()
        self.trunk_qcolors = {k: QColor(*v) for k, v in TRUNK_COLORS.items()}
        self.canopy_qcolors = {k: QColor(*v) for k, v in CANOPY_COLORS.items()}

    def update(self, wind_wave):
        local = self.noise_gen.next()
        self.sway = (wind_wave * 0.3 + local * 0.2) * self.sway_base

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        for dx, dy, part in self.pixels:
            if part in ('trunk', 'trunk_dark'):
                sway_amount = 0
                c = self.trunk_qcolors.get(part, self.trunk_qcolors['trunk'])
            else:
                canopy_height = self.max_dy - self.trunk_h
                if canopy_height > 0:
                    canopy_ratio = max(0, dy - self.trunk_h) / canopy_height
                else:
                    canopy_ratio = 0
                sway_amount = self.sway * canopy_ratio
                c = self.canopy_qcolors.get(part, self.canopy_qcolors['canopy'])
            draw_x = int(self.base_x + (dx + sway_amount) * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = apply_tint(c, tint)
            c.setAlpha(alpha)
            painter.fillRect(draw_x, draw_y, ps, ps, c)


# --- Traveler ---
class Traveler:
    def __init__(self, x, y, traveler_type, direction, speed):
        self.x = float(x)
        self.y = y
        self.frames = traveler_type['frames']
        self.colors = {k: QColor(*v) for k, v in traveler_type['colors'].items()}
        self.direction = direction
        self.speed = speed
        self.frame = 0
        self.frame_counter = 0

    def update(self, screen_width):
        self.x += self.speed * self.direction
        self.frame_counter += 1
        if self.frame_counter >= 18:
            self.frame_counter = 0
            self.frame = 1 - self.frame
        margin = 40
        if self.x > screen_width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = screen_width + margin

    def draw(self, painter, alpha=255, tint=None):
        ps = PIXEL_SIZE
        shape = self.frames[self.frame]
        for dx, dy, part in shape:
            actual_dx = dx * self.direction
            sx = int(self.x + actual_dx * ps)
            sy = int(self.y + dy * ps)
            c = self.colors.get(part)
            if c is None:
                continue
            c = apply_tint(c, tint) if tint else QColor(c)
            c.setAlpha(alpha)
            painter.fillRect(sx, sy, ps, ps, c)


# --- Pine tree generation ---
def _generate_pine_tree(height, rng):
    pixels = []
    trunk_h = max(3, int(height * 0.38))
    lean = rng.uniform(-0.08, 0.08)

    # Trunk
    for dy in range(trunk_h):
        lx = round(lean * dy)
        pixels.append((lx, dy, 'trunk'))
        if dy == 0:
            pixels.append((lx - 1, 0, 'trunk_dark'))
            pixels.append((lx + 1, 0, 'trunk_dark'))

    # Canopy layers
    canopy_h = height - trunk_h
    num_layers = max(2, canopy_h // 3)
    for i in range(num_layers):
        cy = trunk_h + int(i * canopy_h / num_layers)
        lx_base = round(lean * cy)
        w = max(1, int((num_layers - i) * 1.8) + rng.randint(-1, 1))
        for row in range(2):
            for ddx in range(-w, w + 1):
                if abs(ddx) == w:
                    part = 'canopy_dark'
                elif abs(ddx) >= w - 1:
                    part = 'canopy'
                else:
                    part = 'canopy_bright' if row == 0 else 'canopy'
                pixels.append((lx_base + ddx, cy + row, part))
        # Gap between layers (skip a row for the layered look)

    # Tip
    tip_dy = height
    tip_lx = round(lean * tip_dy)
    pixels.append((tip_lx, tip_dy, 'canopy_tip'))
    pixels.append((tip_lx, tip_dy + 1, 'canopy_tip'))

    max_dy = max(p[1] for p in pixels)
    return pixels, trunk_h, max_dy


# --- TokaidoScene ---
class TokaidoScene(BaseScene):
    BASE_WIDTH = 2400

    def __init__(self):
        self.trees = []
        self.travelers = []
        self.widget_width = 0
        self.area_height = 200

    def get_area_height(self, config):
        return 200

    def rebuild(self, config, screen_width, widget_width):
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed)
        wind = config.get("wind", 50)
        ratio = screen_width / self.BASE_WIDTH
        self._generate_trees(rng, widget_width, wind, ratio)
        self._generate_travelers(rng, widget_width, ratio)

    def _generate_trees(self, rng, width, wind, ratio):
        self.trees = []
        tree_count = max(3, int(12 * ratio))
        gap_min, gap_max = 80, 250
        x = rng.randint(20, 80)
        placed = 0
        while x < width and placed < tree_count:
            height = rng.randint(14, 28)
            sway_base = rng.uniform(0.5, 1.5) * (wind / 50)
            pixels, trunk_h, max_dy = _generate_pine_tree(height, rng)
            self.trees.append(PineTree(x, pixels, trunk_h, max_dy, sway_base))
            placed += 1
            x += rng.randint(gap_min, gap_max)

    def _generate_travelers(self, rng, width, ratio):
        self.travelers = []
        road_y = self.area_height
        num_travelers = max(3, int(8 * ratio))
        for _ in range(num_travelers):
            x = rng.randint(0, width)
            t_type = rng.choice(TRAVELER_TYPES)
            direction = rng.choice([-1, 1])
            speed = rng.uniform(0.15, 0.5)
            if t_type['name'] == 'hikyaku':
                speed = rng.uniform(0.5, 0.9)
            self.travelers.append(
                Traveler(x, road_y, t_type, direction, speed))

    def update(self, wind_sim):
        for tree in self.trees:
            wave = wind_sim.get_wave_at(tree.base_x)
            tree.update(wave)
        for trav in self.travelers:
            trav.update(self.widget_width)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        # Sky gradient (subtle)
        sky = QLinearGradient(0, 0, 0, ground_y)
        sky.setColorAt(0.0, QColor(180, 210, 235, 0))
        sky.setColorAt(0.6, QColor(180, 210, 235, 0))
        sky.setColorAt(1.0, QColor(210, 200, 170, 20))
        painter.fillRect(0, 0, self.widget_width, ground_y, sky)

        # Road surface (dirt path)
        road_h = 3 * PIXEL_SIZE
        road_color = QColor(185, 165, 120, 160)
        painter.fillRect(0, ground_y - road_h, self.widget_width, road_h, road_color)
        # Road edge (darker line at top of road)
        edge_color = QColor(140, 120, 80, 120)
        painter.fillRect(0, ground_y - road_h, self.widget_width, PIXEL_SIZE // 2, edge_color)

        # Trees (behind travelers)
        for tree in self.trees:
            alpha = get_alpha(tree.base_x) if get_alpha else 255
            tree.draw(painter, ground_y, alpha, tint)

        # Travelers
        for trav in self.travelers:
            alpha = get_alpha(int(trav.x)) if get_alpha else 255
            trav.draw(painter, alpha, tint)
