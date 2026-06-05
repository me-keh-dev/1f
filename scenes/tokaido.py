"""Tokaido scene - Edo-period pine-lined road with travelers"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint
from scenes.grass import generate_slim_grass, GrassBlade, PALETTE_PRESETS
from PyQt5.QtGui import QColor, QLinearGradient, QPainterPath


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

# 飛脚 (courier/runner) - headband, dynamic running pose, wide stride
HIKYAKU_FRAMES = [
    [   # Frame 0 - leaning forward, wide stride
        (1, -7, 'headband'), (2, -7, 'headband'),
        (0, -6, 'head'), (1, -6, 'head'),
        (0, -5, 'body'),
        (-1, -4, 'body'), (0, -4, 'body'), (1, -4, 'arm'),
        (0, -3, 'body'),
        (0, -2, 'body'),
        (2, -1, 'legs'),
        (-2, 0, 'legs'),
    ],
    [   # Frame 1 - legs swapped
        (1, -7, 'headband'), (2, -7, 'headband'),
        (0, -6, 'head'), (1, -6, 'head'),
        (0, -5, 'body'),
        (-1, -4, 'body'), (0, -4, 'body'), (1, -4, 'arm'),
        (0, -3, 'body'),
        (0, -2, 'body'),
        (-2, -1, 'legs'),
        (2, 0, 'legs'),
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
        'colors': {'headband': (30, 30, 80), 'head': (220, 190, 150), 'body': (25, 25, 70),
                   'arm': (35, 35, 85), 'legs': (90, 75, 50)},
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
        pass  # Pine trees don't sway

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        for dx, dy, part in self.pixels:
            if part in ('trunk', 'trunk_dark'):
                c = self.trunk_qcolors.get(part, self.trunk_qcolors['trunk'])
            else:
                c = self.canopy_qcolors.get(part, self.canopy_qcolors['canopy'])
            draw_x = int(self.base_x + dx * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = apply_tint(c, tint)
            c.setAlpha(alpha)
            painter.fillRect(draw_x, draw_y, ps, ps, c)


# --- Willow tree (柳) ---
WILLOW_LEAF_COLORS = [
    (60, 100, 40),    # 0: dark
    (80, 130, 50),    # 1: mid
    (110, 165, 65),   # 2: bright
    (145, 195, 85),   # 3: tip
]


class WillowTree:
    """Willow tree: trunk + parabolic drooping branches"""
    def __init__(self, base_x, trunk_pixels, branch_data, max_dy, sway_base, leaf_thickness=4):
        self.base_x = base_x
        self.trunk_pixels = trunk_pixels
        self.branch_data = branch_data
        self.max_dy = max(max_dy, 1)
        self.leaf_thickness = leaf_thickness
        self.sway = 0.0
        self.sway_vel = 0.0
        self.sway_base = sway_base
        self.noise_gen = PinkNoiseGenerator()
        # Shared noise generators (4 groups instead of per-branch)
        self._noise_groups = [PinkNoiseGenerator() for _ in range(4)]
        self.branch_offsets = [0.0] * len(branch_data)
        self.trunk_colors = {k: QColor(*v) for k, v in TRUNK_COLORS.items()}
        self.leaf_colors = [QColor(*c) for c in WILLOW_LEAF_COLORS]

    def update(self, wind_wave):
        local = self.noise_gen.next()
        target = (wind_wave * 2.0 + local * 1.2) * self.sway_base
        force = (target - self.sway) * 0.012
        self.sway_vel += force
        self.sway_vel *= 0.96  # high damping → smooth deceleration
        self.sway += self.sway_vel
        # Branch offsets also smoothed
        group_vals = [ng.next() for ng in self._noise_groups]
        for i in range(len(self.branch_offsets)):
            g = i % 4
            target_offset = group_vals[g] * self.sway_base * 1.5
            self.branch_offsets[i] += (target_offset - self.branch_offsets[i]) * 0.03

    def draw(self, painter, ground_y, alpha=255, tint=None, get_alpha=None):
        ps = PIXEL_SIZE
        lw = self.leaf_thickness
        # Single alpha for whole tree (not per-pixel)
        ta = get_alpha(int(self.base_x)) if get_alpha else alpha
        if ta <= 0:
            return
        # Pre-compute tinted colors with alpha baked in (no per-pixel QColor creation)
        tc = {k: apply_tint(v, tint) for k, v in self.trunk_colors.items()}
        for c in tc.values():
            c.setAlpha(ta)
        # 4 leaf shades × 4 alpha bands = 16 pre-built colors
        lc_bands = []
        for shade_c in self.leaf_colors:
            c_base = apply_tint(shade_c, tint)
            band = []
            for a_mult in [0.50, 0.58, 0.65, 0.72, 0.80, 0.85]:
                c = QColor(c_base)
                c.setAlpha(int(ta * a_mult))
                band.append(c)
            lc_bands.append(band)
        # Trunk
        tc_default = tc.get('trunk')
        for dx, dy, part in self.trunk_pixels:
            painter.fillRect(int(self.base_x + dx * ps),
                             int(ground_y - (dy + 1) * ps), ps, ps,
                             tc.get(part, tc_default))
        # Branches — bend with power curve (しなる)
        bx_base = self.base_x
        for bi, branch in enumerate(self.branch_data):
            be = self.branch_offsets[bi] if bi < len(self.branch_offsets) else 0
            sway_total = self.sway + be
            n = max(1, len(branch) - 1)
            for i, (bx, by, shade) in enumerate(branch):
                t = i / n
                bend = t * t
                vy = sway_total * bend * 0.15
                # Pick pre-computed color band (no QColor creation)
                band_idx = min(5, int(t * 6))
                painter.fillRect(int(bx_base + (bx + sway_total * bend) * ps),
                                 int(ground_y - (by + vy + 1) * ps), lw, ps,
                                 lc_bands[shade][band_idx])


# --- Tea house (茶屋) ---
TEA_HOUSE_COLORS = {
    'roof':      QColor(70, 65, 58),
    'roof_edge': QColor(50, 45, 38),
    'wall':      QColor(225, 218, 200),
    'wall_wood': QColor(160, 130, 90),
    'wall_dark': QColor(100, 80, 55),
    'lattice':   QColor(85, 65, 40),
    'noren':     QColor(185, 28, 22),
    'noren_light': QColor(215, 50, 38),
    'post':      QColor(95, 68, 38),
    'sign':      QColor(200, 180, 130),
    'torii':     QColor(175, 28, 18),
    'torii_dark': QColor(140, 20, 12),
}

def _R(x1, x2, y, part):
    """Row of pixels"""
    return [(x, y, part) for x in range(x1, x2+1)]

def _rect(x1, x2, y1, y2, part):
    return [(x, y, part) for x in range(x1, x2+1) for y in range(y1, y2+1)]

def _edo_roof(hw, base_y, rows=3):
    """Prominent Edo-style tiled roof with overhang"""
    px = []
    for r in range(rows):
        w = hw + 2 - r
        if w < 1: w = 1
        y = base_y + r
        for x in range(-w, w+1):
            px.append((x, y, 'roof_edge' if abs(x) >= w else 'roof'))
    return px

# --- 茶屋 (Tea shop): wide, noren, bench ---
TEA_HOUSE_PIXELS = (
    _rect(-10, 10, 1, 2, 'wall_dark') +
    _rect(-10, 10, 3, 7, 'wall') +
    _rect(-10, -10, 1, 7, 'post') + _rect(10, 10, 1, 7, 'post') + _rect(0, 0, 1, 7, 'post') +
    _rect(-9, -7, 5, 6, 'lattice') + _rect(7, 9, 5, 6, 'lattice') +
    _rect(-3, -1, 4, 6, 'noren') + _rect(1, 3, 4, 6, 'noren') +
    [(-3, 6, 'noren_light'), (0, 6, 'noren_light'), (3, 6, 'noren_light'),
     (-3, 3, 'noren'), (-1, 3, 'noren'), (1, 3, 'noren'), (3, 3, 'noren')] +
    _R(-11, 11, 8, 'roof_edge') + _edo_roof(10, 9, 3) +
    _R(-9, -5, 2, 'post') + [(-9, 1, 'post')]
)

# --- 旅籠 (Inn): 2 story, wide ---
INN_PIXELS = (
    _rect(-12, 12, 1, 2, 'wall_dark') +
    _rect(-12, 12, 3, 7, 'wall') +
    _rect(-12, -12, 1, 7, 'post') + _rect(12, 12, 1, 7, 'post') +
    _rect(-5, -5, 1, 7, 'post') + _rect(5, 5, 1, 7, 'post') +
    _rect(-11, -8, 5, 6, 'lattice') + _rect(8, 11, 5, 6, 'lattice') +
    _rect(-3, -1, 4, 6, 'noren') + _rect(1, 3, 4, 6, 'noren') +
    [(-3, 6, 'noren_light'), (0, 6, 'noren_light'), (3, 6, 'noren_light')] +
    _R(-13, 13, 8, 'roof_edge') + _R(-12, 12, 9, 'roof') +
    _rect(-12, 12, 10, 13, 'wall') +
    _rect(-12, -12, 10, 13, 'post') + _rect(12, 12, 10, 13, 'post') +
    _rect(-5, -5, 10, 13, 'post') + _rect(5, 5, 10, 13, 'post') +
    _rect(-10, -8, 11, 12, 'lattice') + _rect(-3, -1, 11, 12, 'lattice') +
    _rect(1, 3, 11, 12, 'lattice') + _rect(8, 10, 11, 12, 'lattice') +
    _R(-13, 13, 14, 'roof_edge') + _edo_roof(12, 15, 4) +
    [(13, 12, 'sign'), (13, 11, 'sign'), (13, 10, 'noren')]
)

# --- 商家 (Merchant shop): lattice-heavy ---
SHOP_PIXELS = (
    _rect(-9, 9, 1, 2, 'wall_dark') +
    _rect(-9, 9, 3, 8, 'wall') +
    _rect(-9, -9, 1, 8, 'post') + _rect(9, 9, 1, 8, 'post') + _rect(0, 0, 1, 8, 'post') +
    _rect(-8, -5, 4, 7, 'lattice') + _rect(-3, -1, 4, 7, 'lattice') +
    _rect(1, 3, 4, 7, 'lattice') + _rect(5, 8, 4, 7, 'lattice') +
    [(-1, 3, 'wall_dark'), (0, 3, 'wall_dark'), (1, 3, 'wall_dark')] +
    [(10, 7, 'sign'), (10, 6, 'sign'), (10, 5, 'noren')] +
    _R(-10, 10, 9, 'roof_edge') + _edo_roof(9, 10, 3)
)

# --- 蔵 (Storehouse): thick white walls ---
KURA_PIXELS = (
    _rect(-8, 8, 1, 3, 'wall_dark') +
    _rect(-8, 8, 4, 10, 'wall') +
    _rect(-8, -8, 1, 10, 'post') + _rect(8, 8, 1, 10, 'post') +
    [(-4, 7, 'lattice'), (-3, 7, 'lattice'), (3, 7, 'lattice'), (4, 7, 'lattice')] +
    _rect(-1, 1, 2, 5, 'wall_dark') + [(0, 6, 'post')] +
    _R(-9, 9, 11, 'roof_edge') + _edo_roof(8, 12, 3)
)

# --- 民家 (House): simple ---
HOUSE_PIXELS = (
    _rect(-8, 8, 1, 2, 'wall_dark') +
    _rect(-8, 8, 3, 6, 'wall_wood') +
    _rect(-8, -8, 1, 6, 'post') + _rect(8, 8, 1, 6, 'post') + _rect(0, 0, 1, 6, 'post') +
    [(-5, 4, 'lattice'), (-5, 5, 'lattice'), (-4, 4, 'lattice'), (-4, 5, 'lattice'),
     (4, 4, 'lattice'), (4, 5, 'lattice'), (5, 4, 'lattice'), (5, 5, 'lattice')] +
    [(-1, 3, 'wall_dark'), (0, 3, 'wall_dark'), (1, 3, 'wall_dark')] +
    _R(-9, 9, 7, 'roof_edge') + _edo_roof(8, 8, 3)
)

# --- 鳥居 (Torii gate) ---
TORII_PIXELS = (
    _rect(-5, -5, 1, 12, 'torii') + _rect(-4, -4, 1, 12, 'torii_dark') +
    _rect(4, 4, 1, 12, 'torii_dark') + _rect(5, 5, 1, 12, 'torii') +
    _R(-7, 7, 13, 'torii') + _R(-7, 7, 14, 'torii_dark') +
    _R(-6, 6, 10, 'torii')
)


class TeaHouse:
    def __init__(self, base_x):
        self.base_x = base_x
        self.pixels = TEA_HOUSE_PIXELS
        self.noren_sway = 0.0
        self.noise_gen = PinkNoiseGenerator()

    def update(self, wind_wave):
        local = self.noise_gen.next()
        self.noren_sway = (wind_wave * 0.15 + local * 0.1)

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        for dx, dy, part in self.pixels:
            sway = 0
            if part in ('noren', 'noren_light'):
                sway = self.noren_sway * (1.0 if dy <= 4 else 0.5)
            draw_x = int(self.base_x + (dx + sway) * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = TEA_HOUSE_COLORS.get(part, TEA_HOUSE_COLORS['wall'])
            c = apply_tint(QColor(c), tint)
            c.setAlpha(alpha)
            painter.fillRect(draw_x, draw_y, ps, ps, c)



# --- Hill (丘) background ---
class Hill:
    def __init__(self, base_x, width, height):
        self.base_x = base_x
        self.width = width
        self.height = height
        self.color = QColor(160, 195, 130, 100)
        self.color_dark = QColor(130, 170, 105, 80)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        ps = PIXEL_SIZE
        cx = self.base_x
        for dx in range(-self.width, self.width + 1):
            ratio = 1.0 - (dx / self.width) ** 2
            h = max(0, int(self.height * math.sqrt(max(0, ratio))))
            if h <= 0:
                continue
            draw_x = int(cx + dx * ps)
            a = get_alpha(draw_x) if get_alpha else 255
            if a <= 0:
                continue
            for dy in range(h):
                base_c = self.color if dy > h * 0.3 else self.color_dark
                c = apply_tint(base_c, tint) if tint else QColor(base_c)
                c.setAlpha(int(c.alpha() * a / 255))
                draw_y = int(ground_y - (dy + 1) * ps)
                painter.fillRect(draw_x, draw_y, ps, ps, c)


# --- Mt. Fuji (富士山) accurate silhouette from Tokaido ---
# Normalized profile: (x_norm, y_norm) where x=-1..1, y=0..1
# Tokaido silhouette — from reference diagram with labeled key points
_FUJI_PROFILE_RAW = [
    # Left Skirt Edge
    (-10.0, 0.013),
    (-8.0, 0.063),
    (-6.0, 0.287),
    (-4.0, 0.850),
    (-3.0, 1.500),
    (-2.0, 2.500),
    (-1.5, 3.200),
    # Left slope approaching summit
    (-1.0, 3.612),
    (-0.7, 3.700),
    # West Crater Rim
    (-0.5, 3.700),
    (-0.3, 3.696),
    # Crater Center (dip)
    (0.0, 3.696),
    (0.1, 3.696),
    # Highest Peak (Kengamine)
    (0.2, 3.693),
    (0.4, 3.691),
    (0.72, 3.691),
    # Right slope descending
    (1.0, 3.600),
    (1.5, 3.200),
    (2.0, 2.500),
    (3.0, 1.500),
    # Hoei-zan area
    (4.0, 1.050),
    (5.0, 0.550),
    (6.0, 0.287),
    (8.0, 0.063),
    # Right Skirt Edge
    (10.0, 0.013),
]
_FUJI_X_MIN = -10.0
_FUJI_X_MAX = 10.0
_FUJI_Y_MAX = 3.700
# Stretch lower 2/3 of mountain by 3x horizontally
_FUJI_HEIGHT_THRESHOLD = _FUJI_Y_MAX * (2.0 / 3.0)
_FUJI_STRETCH = 3.0
# Find x bounds where height crosses threshold (~x=-2 and x=2)
_FUJI_SUMMIT_LEFT = -2.0
_FUJI_SUMMIT_RIGHT = 2.0

_FUJI_SUMMIT_SCALE_X = 1.0 / 3.0  # width: 1/6 × 2 = 1/3
_FUJI_SUMMIT_SCALE_Y = 1.0 / 12.0  # height: 1/6 × 1/2 = 1/12

def _transform_point(x, y):
    if _FUJI_SUMMIT_LEFT <= x <= _FUJI_SUMMIT_RIGHT:
        new_x = x * _FUJI_SUMMIT_SCALE_X
        new_y = _FUJI_HEIGHT_THRESHOLD + (y - _FUJI_HEIGHT_THRESHOLD) * _FUJI_SUMMIT_SCALE_Y
        return new_x, new_y
    elif x < _FUJI_SUMMIT_LEFT:
        new_left = _FUJI_SUMMIT_LEFT * _FUJI_SUMMIT_SCALE_X
        return new_left + (x - _FUJI_SUMMIT_LEFT) * _FUJI_STRETCH, y
    else:
        new_right = _FUJI_SUMMIT_RIGHT * _FUJI_SUMMIT_SCALE_X
        return new_right + (x - _FUJI_SUMMIT_RIGHT) * _FUJI_STRETCH, y

_FUJI_PROFILE_STRETCHED = [_transform_point(x, y) for x, y in _FUJI_PROFILE_RAW]
_FUJI_SX_MIN = _FUJI_PROFILE_STRETCHED[0][0]
_FUJI_SX_MAX = _FUJI_PROFILE_STRETCHED[-1][0]
_FUJI_SX_CENTER = (_FUJI_SX_MIN + _FUJI_SX_MAX) / 2.0
_FUJI_SX_RANGE = _FUJI_SX_MAX - _FUJI_SX_MIN

FUJI_PROFILE = [
    ((x - _FUJI_SX_CENTER) / (_FUJI_SX_RANGE / 2.0), y / _FUJI_Y_MAX)
    for x, y in _FUJI_PROFILE_STRETCHED
]

def _fuji_height_at(x_norm):
    """Interpolate Fuji profile height at normalized x (-1..1) → height (0..1)"""
    for i in range(len(FUJI_PROFILE) - 1):
        x0, y0 = FUJI_PROFILE[i]
        x1, y1 = FUJI_PROFILE[i + 1]
        if x0 <= x_norm <= x1:
            t = (x_norm - x0) / (x1 - x0) if x1 != x0 else 0
            return y0 + (y1 - y0) * t
    return 0.0


class MtFuji:
    def __init__(self, base_x, half_width, max_height):
        self.base_x = base_x
        self.half_width = half_width  # in pixels
        self.max_height = max_height  # in pixels
        self.body_color = QColor(80, 90, 130, 120)
        self.snow_color = QColor(220, 228, 240, 160)
        self.snow_threshold = 0.72  # above this ratio = snow

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        from PyQt5.QtGui import QPainter
        cx = self.base_x
        screen_hw = self.half_width * PIXEL_SIZE
        screen_h = self.max_height * PIXEL_SIZE
        road_h = 3 * PIXEL_SIZE
        base_y = ground_y - road_h

        # Build smooth ridgeline path
        body_path = QPainterPath()
        snow_path = QPainterPath()
        body_path.moveTo(cx - screen_hw, base_y)
        snow_path_started = False
        snow_last_x = 0
        snow_y_threshold = screen_h * self.snow_threshold

        step = 2
        for sx in range(-screen_hw, screen_hw + 1, step):
            x_norm = sx / screen_hw  # linear mapping
            h_ratio = _fuji_height_at(x_norm)
            col_h = screen_h * h_ratio
            px = cx + sx
            py = base_y - col_h
            body_path.lineTo(px, py)
            # Snow cap path — only where height exceeds snow line
            if col_h > snow_y_threshold:
                if not snow_path_started:
                    snow_path.moveTo(px, base_y - snow_y_threshold)
                    snow_path_started = True
                snow_path.lineTo(px, py)
                snow_last_x = px
            elif snow_path_started:
                # Snow region ended — close at snow line
                snow_path.lineTo(snow_last_x, base_y - snow_y_threshold)
                snow_path.closeSubpath()
                snow_path_started = False

        body_path.lineTo(cx + screen_hw, base_y)
        body_path.closeSubpath()

        # Close snow path if still open
        if snow_path_started:
            snow_path.lineTo(snow_last_x, base_y - snow_y_threshold)
            snow_path.closeSubpath()

        # Mouse fade — use minimum alpha across mountain width for consistent fade
        if get_alpha:
            # Sample multiple points across the mountain base
            samples = [get_alpha(int(cx + sx)) for sx in range(-screen_hw, screen_hw + 1, max(1, screen_hw // 3))]
            a = min(samples)
            painter.setOpacity(a / 255.0)

        # Draw with antialiasing
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Body with gradient: base color → white at summit
        body_grad = QLinearGradient(cx, base_y, cx, base_y - screen_h)
        body_base = apply_tint(QColor(self.body_color), tint) if tint else QColor(self.body_color)
        snow_top = apply_tint(QColor(255, 255, 255, body_base.alpha()), tint) if tint else QColor(255, 255, 255, body_base.alpha())
        body_grad.setColorAt(0.0, body_base)
        body_grad.setColorAt(0.3, body_base)
        body_grad.setColorAt(1.0, snow_top)
        from PyQt5.QtGui import QBrush
        painter.fillPath(body_path, QBrush(body_grad))

        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setOpacity(1.0)

        painter.setRenderHint(QPainter.Antialiasing, False)


# --- Generic static building ---
class StaticBuilding:
    """Reusable for any building defined as pixel list"""
    def __init__(self, base_x, pixels, has_noren=False):
        self.base_x = base_x
        self.pixels = pixels
        self.has_noren = has_noren
        self.noren_sway = 0.0
        self.noise_gen = PinkNoiseGenerator() if has_noren else None

    def update(self, wind_wave):
        if self.has_noren and self.noise_gen:
            local = self.noise_gen.next()
            self.noren_sway = (wind_wave * 0.15 + local * 0.1)

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        for dx, dy, part in self.pixels:
            sway = 0
            if self.has_noren and part in ('noren', 'noren_light'):
                sway = self.noren_sway * (0.8 if dy <= 5 else 0.4)
            draw_x = int(self.base_x + (dx + sway) * ps)
            draw_y = int(ground_y - (dy + 1) * ps)
            c = TEA_HOUSE_COLORS.get(part, TEA_HOUSE_COLORS['wall'])
            c = apply_tint(QColor(c), tint)
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
        self.is_runner = traveler_type['name'] == 'hikyaku'
        self.frame = 0
        self.frame_counter = 0

    def update(self, screen_width):
        self.x += self.speed * self.direction
        self.frame_counter += 1
        frame_rate = 8 if self.is_runner else 18  # runners animate faster
        if self.frame_counter >= frame_rate:
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


# --- Pine tree generation (Japanese-style curved pine) ---
def _flat_canopy(cx, cy, half_w, rng):
    """Generate a flat, parasol-shaped canopy cluster at (cx, cy)"""
    pixels = []
    # Slightly irregular width
    w_variation = rng.randint(-1, 1)
    w = half_w + w_variation
    # Top surface (bright, wide)
    for cdx in range(-w, w + 1):
        part = 'canopy_dark' if abs(cdx) == w else 'canopy_bright'
        pixels.append((cx + cdx, cy, part))
    # Middle layer (slightly narrower)
    mid_w = max(1, w - 1)
    for cdx in range(-mid_w, mid_w + 1):
        part = 'canopy_dark' if abs(cdx) == mid_w else 'canopy'
        pixels.append((cx + cdx, cy - 1, part))
    # Underside (darker, much narrower — gives depth)
    under_w = max(1, w - rng.randint(1, 2))
    for cdx in range(-under_w, under_w + 1):
        pixels.append((cx + cdx, cy + 1, 'canopy_dark'))
    return pixels


def _generate_pine_tree(height, rng):
    pixels = []

    # S-curved trunk — thick at base, winding upward
    lean_dir = rng.choice([-1, 1])
    lean_strength = rng.uniform(0.2, 0.4)
    curve_freq = rng.uniform(0.08, 0.15)  # S-curve frequency
    trunk_h = height
    cx = 0.0
    trunk_positions = []
    for dy in range(trunk_h):
        # S-curve: sine wave + increasing lean
        cx += lean_dir * lean_strength + math.sin(dy * curve_freq) * 0.6
        lx = round(cx)
        pixels.append((lx, dy, 'trunk'))
        # Thick base tapering up
        if dy < 5:
            pixels.append((lx - 1, dy, 'trunk_dark'))
            pixels.append((lx + 1, dy, 'trunk_dark'))
            if dy < 2:
                pixels.append((lx - 2, dy, 'trunk_dark'))
                pixels.append((lx + 2, dy, 'trunk_dark'))
        elif dy < 10:
            pixels.append((lx - 1, dy, 'trunk_dark'))
        trunk_positions.append((lx, dy))

    # Branches extending horizontally with flat canopy at tips
    num_branches = rng.randint(3, 5)
    branch_zone_start = max(4, trunk_h // 3)
    used_dy = set()
    for _ in range(num_branches):
        for _attempt in range(10):
            branch_dy = rng.randint(branch_zone_start, trunk_h - 2)
            if all(abs(branch_dy - u) >= 3 for u in used_dy):
                used_dy.add(branch_dy)
                break
        else:
            continue
        trunk_x = trunk_positions[branch_dy][0]
        branch_dir = rng.choice([-1, 1])
        branch_len = rng.randint(3, 6)
        # Draw branch (slightly curving upward)
        bx = trunk_x
        by = branch_dy
        for bi in range(1, branch_len + 1):
            bx += branch_dir
            if bi % 2 == 0:
                by += 1
            pixels.append((bx, by, 'trunk'))
        # Flat canopy at branch tip
        canopy_w = rng.randint(3, 5)
        pixels.extend(_flat_canopy(bx, by, canopy_w, rng))

    # Top canopy (always present, larger)
    top_x, top_y = trunk_positions[-1]
    top_w = rng.randint(3, 5)
    pixels.extend(_flat_canopy(top_x, top_y + 1, top_w, rng))

    # Extra canopy near top for fullness
    if rng.random() < 0.7 and len(trunk_positions) > 6:
        near_idx = rng.randint(2, min(5, len(trunk_positions) - 1))
        near_x, near_y = trunk_positions[-near_idx]
        extra_dir = -lean_dir
        ex = near_x + extra_dir * rng.randint(2, 5)
        pixels.extend(_flat_canopy(ex, near_y, rng.randint(2, 4), rng))
        # Branch connecting to it
        for bi in range(1, abs(ex - near_x)):
            bxi = near_x + extra_dir * bi
            pixels.append((bxi, near_y, 'trunk'))

    max_dy = max(p[1] for p in pixels)
    return pixels, trunk_h // 3, max_dy


# --- Willow tree generation (3-layer: trunk → main branches → drooping strands) ---
def _generate_willow(height, rng, config=None):
    trunk_pixels = []
    branch_data = []  # list of [(x, y, shade), ...] per strand

    # --- Layer 1: Trunk (curved, tapering) ---
    trunk_h = max(6, int(height * rng.uniform(0.35, 0.48)))
    lean = rng.uniform(-0.1, 0.1)
    curve = rng.uniform(-0.006, 0.006)
    base_width = rng.randint(2, 4)
    cx = 0.0
    for dy in range(trunk_h):
        cx += lean + curve * dy
        lx = round(cx)
        trunk_pixels.append((lx, dy, 'trunk'))
        w = max(0, base_width - dy * base_width // trunk_h)
        for wx in range(1, w + 1):
            trunk_pixels.append((lx - wx, dy, 'trunk_dark'))
            trunk_pixels.append((lx + wx, dy, 'trunk_dark'))

    trunk_top_x = round(cx)
    trunk_top_y = trunk_h

    # --- Layer 2: Main branches (大枝, 3-5 short thick branches going up/outward) ---
    branch_count = rng.randint(3, 5)
    angle_bias = rng.uniform(-15, 15)  # per-tree lean tendency
    branch_tips = []  # (tip_x, tip_y) + midpoints for strand attachment

    for bi in range(branch_count):
        # Spread branches evenly with randomness
        base_angle = -60 + (120 / max(1, branch_count - 1)) * bi + angle_bias
        base_angle += rng.uniform(-15, 15)
        angle_rad = math.radians(90 + base_angle)  # 90=straight up, ±60=sides
        branch_len = rng.randint(3, 6)
        bx = float(trunk_top_x)
        by = float(trunk_top_y)
        for step in range(branch_len):
            bx += math.cos(angle_rad) * 0.8
            by += math.sin(angle_rad) * 0.8
            trunk_pixels.append((round(bx), round(by), 'trunk'))
            if step > 0:
                trunk_pixels.append((round(bx), round(by) - 1, 'trunk_dark'))
            # Collect attachment points along branch
            if step >= branch_len // 2:
                branch_tips.append((bx, by))
        branch_tips.append((bx, by))  # tip

    # --- Layer 3: Drooping strands (parabolic fountain from branch tips) ---
    leaf_thickness = config.get("tk_leaf_thickness", 4) if config else 4
    base_strand_count = 30
    thickness_ratio = 4.0 / max(1, leaf_thickness)
    num_strands = int(base_strand_count * thickness_ratio) + rng.randint(-3, 3)
    num_strands = max(12, num_strands)

    spread_mult = rng.uniform(0.8, 1.3)
    gravity_base = rng.uniform(0.025, 0.05)

    for si in range(num_strands):
        # Pick attachment point from branch tips
        tip = rng.choice(branch_tips)
        start_x = tip[0]
        start_y = tip[1]

        # Parabolic: spread outward from branch tip, then droop softly
        spread = (si / max(1, num_strands - 1)) * 2 - 1 + rng.uniform(-0.15, 0.15)
        vx = spread * rng.uniform(0.35, 0.7) * spread_mult
        vy = rng.uniform(0.02, 0.15)
        gravity = gravity_base + rng.uniform(-0.01, 0.01)
        strand_len = rng.randint(max(15, height), max(25, int(height * 1.5)))

        strand = []
        x = start_x
        y = start_y
        for step in range(strand_len):
            x += vx
            y += vy
            vy -= gravity
            vx *= 0.94
            if y < 0.5:
                break
            t = step / max(1, strand_len - 1)
            shade = 1 if t < 0.3 else (2 if t < 0.6 else 3)
            strand.append((x, y, shade))
        if strand:
            branch_data.append(strand)

    return trunk_pixels, branch_data, trunk_h


# --- TokaidoScene ---
class TokaidoScene(BaseScene):
    BASE_WIDTH = 2400

    def __init__(self):
        self.fuji = None
        self.hills = []
        self.back_trees = []
        self.back_willows = []
        self.front_trees = []
        self.front_willows = []
        self.buildings = []
        self.roadside_grass = []
        self.travelers = []
        self.widget_width = 0
        self.area_height = 200

    def get_area_height(self, config):
        willow_max = config.get("tk_willow_max_h", 45)
        return max(200, int(willow_max * PIXEL_SIZE * 0.7) + 50)

    def rebuild(self, config, screen_width, widget_width):
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed)
        wind = config.get("wind", 50)
        ratio = screen_width / self.BASE_WIDTH
        self._generate_scene(rng, widget_width, wind, ratio, config)
        self._generate_fuji(rng, widget_width, config)
        self._generate_roadside_grass(rng, widget_width, wind, config)
        self._generate_travelers(rng, widget_width, ratio, config)

    def _generate_scene(self, rng, width, wind, ratio, config):
        self.hills = []
        self.trees = []
        self.willows = []
        self.back_trees = []
        self.back_willows = []
        self.front_trees = []
        self.front_willows = []
        self.buildings = []

        # Object counts from config (with ratio scaling)
        counts = {
            'pine':    max(0, config.get("tk_pine_count", 2)),
            'willow':  max(0, config.get("tk_willow_count", 2)),
            'teahouse': max(0, config.get("tk_teahouse_count", 2)),
            'inn':     max(0, config.get("tk_inn_count", 1)),
            'shop':    max(0, config.get("tk_shop_count", 2)),
            'kura':    max(0, config.get("tk_kura_count", 1)),
            'house':   max(0, config.get("tk_house_count", 3)),
            'torii':   max(0, config.get("tk_torii_count", 0)),
            'hill':    max(0, config.get("tk_hill_count", 2)),
        }

        # Background hills (drawn behind everything)
        for _ in range(counts['hill']):
            hx = rng.randint(0, width)
            hw = rng.randint(15, 35)
            hh = rng.randint(8, 18)
            self.hills.append(Hill(hx, hw, hh))

        # Building half-widths (in pixels) for adjacent placement
        BUILDING_HW = {'teahouse': 11, 'inn': 13, 'house': 9, 'shop': 10, 'kura': 9, 'torii': 7}

        # Collect building and tree items
        building_items = []
        for _ in range(counts['teahouse']):
            building_items.append('teahouse')
        for _ in range(counts['inn']):
            building_items.append('inn')
        for _ in range(counts['shop']):
            building_items.append('shop')
        for _ in range(counts['kura']):
            building_items.append('kura')
        for _ in range(counts['house']):
            building_items.append('house')
        for _ in range(counts['torii']):
            building_items.append('torii')
        rng.shuffle(building_items)

        tree_items = []
        for _ in range(counts['pine']):
            tree_items.append('pine')
        for _ in range(counts['willow']):
            tree_items.append('willow')
        rng.shuffle(tree_items)

        # Place buildings in connected rows (長屋), with trees between rows
        all_items = []
        bi = 0
        ti = 0
        # Interleave: cluster of 2-4 buildings, then a tree, repeat
        while bi < len(building_items) or ti < len(tree_items):
            remaining = len(building_items) - bi
            cluster_size = rng.randint(1, min(4, remaining)) if remaining > 0 else 0
            for _ in range(cluster_size):
                if bi < len(building_items):
                    all_items.append(building_items[bi])
                    bi += 1
            if ti < len(tree_items):
                all_items.append(tree_items[ti])
                ti += 1

        x = rng.randint(20, 60)
        for item in all_items:
            if x >= width:
                break
            if item == 'pine':
                height = rng.randint(14, 28)
                pixels, trunk_h, max_dy = _generate_pine_tree(height, rng)
                layer = rng.choice(['front', 'back'])
                if layer == 'back':
                    self.back_trees.append(PineTree(x, pixels, trunk_h, max_dy, 0))
                else:
                    self.front_trees.append(PineTree(x, pixels, trunk_h, max_dy, 0))
                x += rng.randint(40, 80)
            elif item == 'willow':
                w_min = config.get("tk_willow_min_h", 45)
                w_max = config.get("tk_willow_max_h", 68)
                height = rng.randint(w_min, max(w_min + 2, w_max))
                sway_base = rng.uniform(1.0, 3.0) * (wind / 50)
                leaf_thickness = config.get("tk_leaf_thickness", 4)
                trunk_px, branch_data, max_dy = _generate_willow(height, rng, config)
                layer = rng.choice(['front', 'back'])
                if layer == 'back':
                    self.back_willows.append(WillowTree(x, trunk_px, branch_data, max_dy, sway_base, leaf_thickness))
                else:
                    self.front_willows.append(WillowTree(x, trunk_px, branch_data, max_dy, sway_base, leaf_thickness))
                x += rng.randint(50, 90)
            else:
                # Building: place adjacent (長屋 style, minimal gap)
                hw = BUILDING_HW.get(item, 9)
                pixels_map = {
                    'teahouse': (TEA_HOUSE_PIXELS, True),
                    'inn': (INN_PIXELS, True),
                    'shop': (SHOP_PIXELS, False),
                    'kura': (KURA_PIXELS, False),
                    'house': (HOUSE_PIXELS, False),
                    'torii': (TORII_PIXELS, False),
                }
                px_data, has_noren = pixels_map.get(item, (HOUSE_PIXELS, False))
                # Place center at x + half-width so buildings touch
                cx = x + hw * PIXEL_SIZE
                self.buildings.append(StaticBuilding(cx, px_data, has_noren=has_noren))
                x = cx + hw * PIXEL_SIZE  # next building starts right at the edge

    def _generate_fuji(self, rng, width, config):
        self.fuji = None
        if not config.get("tk_fuji", True):
            return
        # Collect all occupied x-ranges (buildings + trees)
        occupied = []
        for bld in self.buildings:
            xs = [p[0] for p in bld.pixels]
            left = bld.base_x + min(xs) * PIXEL_SIZE - PIXEL_SIZE * 4
            right = bld.base_x + max(xs) * PIXEL_SIZE + PIXEL_SIZE * 4
            occupied.append((left, right))
        for t in self.back_trees + self.front_trees:
            occupied.append((t.base_x - 40, t.base_x + 40))
        for w in self.back_willows + self.front_willows:
            occupied.append((w.base_x - 60, w.base_x + 60))
        # Find largest empty gap
        occupied.sort()
        fuji_w = 91  # half-width: stretched base (3x below 2/3 height)
        fuji_screen_w = fuji_w * PIXEL_SIZE
        best_x = None
        best_gap = 0
        prev_right = 0
        for left, right in occupied + [(width, width)]:
            gap = left - prev_right
            if gap > best_gap:
                best_gap = gap
                best_x = prev_right + gap // 2
            prev_right = max(prev_right, right)
        if best_x and best_gap > fuji_screen_w:
            fuji_h = rng.randint(20, 30)
            self.fuji = MtFuji(best_x, fuji_w, fuji_h)

    def _generate_roadside_grass(self, rng, width, wind, config):
        self.roadside_grass = []
        grass_count = config.get("tk_grass_count", 60)
        if grass_count <= 0:
            return

        # Collect building x-ranges to avoid placing grass on buildings
        building_zones = []
        for bld in self.buildings:
            bx = bld.base_x
            xs = [p[0] for p in bld.pixels]
            left = bx + min(xs) * PIXEL_SIZE - PIXEL_SIZE * 2
            right = bx + max(xs) * PIXEL_SIZE + PIXEL_SIZE * 2
            building_zones.append((left, right))

        def in_building(x):
            for left, right in building_zones:
                if left <= x <= right:
                    return True
            return False

        palettes = [PALETTE_PRESETS[7]]  # Moss palette
        x = rng.randint(5, 15)
        placed = 0
        while x < width and placed < grass_count:
            if not in_building(x):
                # Short grass, about 1/3 of building height (3-5 pixels)
                height = rng.randint(3, 5)
                pixels, _ = generate_slim_grass(height, rng)
                sway_base = rng.uniform(1.5, 3.5) * (wind / 50)
                data = {
                    "x": x, "pixels": pixels, "palette_idx": 0,
                    "flower_color": None, "sway_base": sway_base,
                    "max_dy": max((p[1] for p in pixels), default=1),
                }
                self.roadside_grass.append(GrassBlade(data, palettes))
                placed += 1
                x += rng.randint(2, 5)  # very dense spacing
            else:
                x += PIXEL_SIZE * 2  # skip past building area

    def _generate_travelers(self, rng, width, ratio, config):
        self.travelers = []
        road_y = self.area_height
        num_travelers = config.get("tk_traveler_count", 6)
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
        for tree in self.back_trees + self.front_trees:
            tree.update(0)
        for willow in self.back_willows + self.front_willows:
            wave = wind_sim.get_wave_at(willow.base_x)
            willow.update(wave)
        for g in self.roadside_grass:
            wave = wind_sim.get_wave_at(g.base_x)
            g.update(wave)
        for bld in self.buildings:
            wave = wind_sim.get_wave_at(bld.base_x)
            bld.update(wave)
        for trav in self.travelers:
            trav.update(self.widget_width)

    def has_background_layer(self):
        return self.fuji is not None

    def draw_background(self, painter, ground_y, tint=None, get_alpha=None):
        if self.fuji:
            self.fuji.draw(painter, ground_y, tint, get_alpha)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        # Sky gradient
        sky = QLinearGradient(0, 0, 0, ground_y)
        sky.setColorAt(0.0, QColor(180, 210, 235, 0))
        sky.setColorAt(0.6, QColor(180, 210, 235, 0))
        sky.setColorAt(1.0, QColor(210, 200, 170, 20))
        painter.fillRect(0, 0, self.widget_width, ground_y, sky)

        # Mt. Fuji is drawn in background layer (behind other windows)

        # Background hills
        for hill in self.hills:
            hill.draw(painter, ground_y, tint, get_alpha)

        # Road surface (with mouse fade, coarse stepping for performance)
        road_h = 3 * PIXEL_SIZE
        step = PIXEL_SIZE * 2
        for rx in range(0, self.widget_width, step):
            a = get_alpha(rx) if get_alpha else 255
            rc = QColor(185, 165, 120, int(160 * a / 255))
            painter.fillRect(rx, ground_y - road_h, step, road_h, rc)
            ec = QColor(140, 120, 80, int(120 * a / 255))
            painter.fillRect(rx, ground_y - road_h, step, PIXEL_SIZE // 2, ec)

        # Back trees (behind buildings, grow from road top line)
        road_top_y = ground_y - road_h
        for tree in self.back_trees:
            alpha = get_alpha(tree.base_x) if get_alpha else 255
            tree.draw(painter, road_top_y, alpha, tint)
        for willow in self.back_willows:
            willow.draw(painter, road_top_y, 255, tint, get_alpha)

        # Buildings
        for bld in self.buildings:
            alpha = get_alpha(bld.base_x) if get_alpha else 255
            bld.draw(painter, ground_y, alpha, tint)

        # Roadside grass (on top of road, behind travelers)
        road_top_y = ground_y - road_h
        grass_ps = 2  # thin pixel size for grass
        for g in self.roadside_grass:
            alpha = get_alpha(g.base_x) if get_alpha else 255
            g.draw(painter, road_top_y, alpha, tint, grass_ps)

        # Travelers (behind front trees)
        for trav in self.travelers:
            alpha = get_alpha(int(trav.x)) if get_alpha else 255
            trav.draw(painter, alpha, tint)

        # Front trees (in front of travelers and buildings)
        for tree in self.front_trees:
            alpha = get_alpha(tree.base_x) if get_alpha else 255
            tree.draw(painter, ground_y, alpha, tint)
        for willow in self.front_willows:
            willow.draw(painter, ground_y, 255, tint, get_alpha)
