"""Takibi (campfire) scene - physically-inspired pixel-art campfire

The flame is a heat-propagation simulation (advection + decay, like the
classic "fire effect"): heat is injected at the base with 1/f yuragi,
rises cell by cell while decaying randomly and drifting with the wind.
The flame silhouette emerges from the physics instead of a fixed shape.
"""
import datetime
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint
from PyQt5.QtGui import QColor, QRadialGradient


# Atmospheric perspective: distant things shift toward this haze blue
HAZE_COLOR = (115, 135, 175)

LOG_COLOR = QColor(95, 62, 35)
LOG_DARK = QColor(70, 45, 25)
LOG_END = QColor(140, 100, 60)
STONE_COLOR = QColor(105, 105, 115)
STONE_DARK = QColor(80, 80, 90)
SMOKE_COLOR = (130, 128, 135)

# Time-of-day phases. The campfire is its own light source, so the scene
# ignores the global lighting tint and instead adapts the whole mood:
#   ambient: base brightness of campers/tent (moonlight / twilight)
#   campers: people are present   fire: the fire is burning
PHASES = {
    "day":       {"ambient": 0.95, "campers": True,  "fire": True},
    "evening":   {"ambient": 0.55, "campers": True,  "fire": True},
    "night":     {"ambient": 0.30, "campers": True,  "fire": True},
    "deepnight": {"ambient": 0.25, "campers": False, "fire": True},
    "dawn":      {"ambient": 0.55, "campers": False, "fire": False},
}

# Heat -> color bands (high heat at bottom/center, low at ragged tips)
HEAT_BANDS = [
    (0.78, QColor(255, 240, 170), 250),  # white-yellow core
    (0.55, QColor(255, 190, 80), 245),
    (0.32, QColor(255, 140, 40), 240),
    (0.14, QColor(220, 70, 15), 225),
    (0.06, QColor(150, 40, 18), 160),    # dying embers at the tips
]

# --- Camper pixel art (side view, sitting, facing +x = toward fire) ---
# (dx, dy): dy positive = up from ground. Firelight comes from +x side.
# Body without the fire-side arm; each pose adds its own arm and props.
_CAMPER_BODY = [
    # Knit cap
    (2, 14), (3, 14), (4, 14),
    (2, 13), (3, 13), (4, 13), (5, 13),
    (2, 12), (2, 11),  # ear flap / back of head
    # Face (front of head)
    (3, 12), (4, 12), (5, 12),
    (3, 11), (4, 11), (5, 11),
    (3, 10), (4, 10),
    # Jacket torso (leaning toward the fire)
    (1, 9), (2, 9), (3, 9), (4, 9),
    (1, 8), (2, 8), (3, 8), (4, 8),
    (1, 7), (2, 7), (3, 7), (4, 7),
    (1, 6), (2, 6), (3, 6), (4, 6),
    (2, 5), (3, 5), (4, 5),
    # Pants: thighs
    (2, 4), (3, 4), (4, 4), (5, 4),
    (2, 3), (3, 3), (4, 3), (5, 3),
    # Pants: shins
    (5, 2), (6, 2), (5, 1), (6, 1),
    # Boots
    (5, 0), (6, 0), (7, 0),
    # Log stump seat
    (0, 3), (1, 3), (0, 2), (1, 2),
    (0, 1), (1, 1), (0, 0), (1, 0),
]


def _camper_part(dx, dy):
    if dy >= 13 or (dx == 2 and dy >= 11):
        return 'cap'
    if dy >= 10 and dx >= 3:
        return 'face'
    if dy >= 5:
        return 'jacket'
    if dx <= 1 and dy <= 3:
        return 'seat'
    if dy == 0:
        return 'boots'
    return 'pants'


# Poses: arm + props, with explicit part names
CAMPER_POSES = {
    # Warming hands over the fire
    "warm": [(5, 8, 'jacket'), (5, 7, 'jacket'), (6, 7, 'jacket'), (6, 6, 'jacket'),
             (7, 6, 'hand')],
    # Roasting a marshmallow on a stick
    "marshmallow": [(5, 8, 'jacket'), (5, 7, 'jacket'), (6, 7, 'jacket'), (6, 6, 'jacket'),
                    (7, 6, 'hand'),
                    (8, 5, 'stick'), (9, 5, 'stick'), (10, 4, 'marshmallow')],
    # Playing guitar on the lap
    "guitar": [(5, 8, 'jacket'), (5, 7, 'jacket'), (6, 6, 'hand'),
               (5, 5, 'guitar'), (6, 5, 'guitar'), (5, 4, 'guitar'), (6, 4, 'guitar'),
               (7, 6, 'guitar_neck'), (8, 7, 'guitar_neck'), (9, 8, 'guitar_neck')],
    # Sipping from a mug
    "mug": [(5, 8, 'jacket'), (6, 8, 'jacket'), (6, 9, 'hand'),
            (6, 10, 'mug'), (7, 10, 'mug')],
}

# Prop colors shared by all campers (hand color comes from the face tone)
_PROP_COLORS = {
    'boots': (52, 42, 38),
    'seat': (110, 75, 45),
    'stick': (150, 110, 60),
    'marshmallow': (246, 240, 228),
    'guitar': (175, 120, 55),
    'guitar_neck': (110, 70, 40),
    'mug': (200, 85, 70),
}

# Clothing palettes: (cap, jacket, pants, face)
CAMPER_PALETTES = [
    {'cap': (205, 65, 60),   'jacket': (72, 95, 150),   'pants': (70, 62, 80),  'face': (235, 180, 140)},
    {'cap': (212, 165, 70),  'jacket': (90, 135, 95),   'pants': (98, 72, 52),  'face': (232, 172, 130)},
    {'cap': (70, 140, 150),  'jacket': (190, 110, 50),  'pants': (60, 70, 90),  'face': (225, 165, 125)},
    {'cap': (135, 85, 155),  'jacket': (115, 115, 125), 'pants': (80, 60, 55),  'face': (238, 185, 150)},
    {'cap': (225, 220, 210), 'jacket': (170, 60, 55),   'pants': (55, 55, 65),  'face': (205, 145, 105)},
    {'cap': (75, 115, 65),   'jacket': (135, 95, 60),   'pants': (75, 80, 70),  'face': (228, 170, 135)},
]


def make_camper_spec(pose, palette_idx):
    """Build one unique camper from a pose and a clothing palette."""
    palette = dict(_PROP_COLORS)
    palette.update(CAMPER_PALETTES[palette_idx % len(CAMPER_PALETTES)])
    palette['hand'] = palette['face']
    cells = [(dx, dy, _camper_part(dx, dy)) for dx, dy in _CAMPER_BODY]
    cells += CAMPER_POSES[pose]
    return {"cells": cells, "palette": palette}


_CAMPER_SPAN = 8.0  # dx range for the lighting gradient

# Tent canvas colors: white, yellow, blue, red, green, teal
TENT_COLORS = [
    (210, 205, 195),
    (205, 170, 60),
    (70, 100, 160),
    (170, 60, 55),
    (80, 120, 75),
    (66, 108, 100),
]
# Glamping bell tents are classic cream canvas
BELL_TENT_COLOR = (225, 218, 200)
# Colorful ball LED string lights decorating glamping sites
LED_COLORS = [
    (255, 95, 95),
    (130, 225, 130),
    (130, 165, 255),
    (255, 220, 110),
    (255, 140, 220),
]


class Spark:
    """Rising ember particle (火の粉)"""
    def __init__(self, x, y, rng, ps):
        self.x = x
        self.y = y
        self.vx = rng.uniform(-0.15, 0.15) * ps
        self.vy = -rng.uniform(0.25, 0.7) * ps
        self.life = rng.randint(50, 140)
        self.age = 0
        self.phase = rng.uniform(0, math.tau)
        self.size = ps if rng.random() < 0.3 else max(1, ps // 2)

    def update(self, wind):
        self.age += 1
        self.x += self.vx + wind * 0.12 + math.sin(self.age * 0.15 + self.phase) * 0.4
        self.y += self.vy
        self.vy *= 0.995

    @property
    def alive(self):
        return self.age < self.life

    def draw(self, painter, tint, fade):
        t = self.age / self.life
        if t < 0.4:
            c = QColor(255, 220, 120)
        elif t < 0.75:
            c = QColor(255, 140, 50)
        else:
            c = QColor(200, 70, 30)
        c = apply_tint(c, tint)
        c.setAlpha(int(255 * (1.0 - t) * fade))
        painter.fillRect(int(self.x), int(self.y), self.size, self.size, c)


class Smoke:
    """Drifting smoke puff"""
    def __init__(self, x, y, rng, ps):
        self.x = x
        self.y = y
        self.vy = -rng.uniform(0.15, 0.35) * ps
        self.life = rng.randint(120, 240)
        self.age = 0
        self.phase = rng.uniform(0, math.tau)
        self.ps = ps

    def update(self, wind):
        self.age += 1
        self.x += wind * 0.2 + math.sin(self.age * 0.04 + self.phase) * 0.3
        self.y += self.vy

    @property
    def alive(self):
        return self.age < self.life

    def draw(self, painter, tint, fade):
        t = self.age / self.life
        size = int(self.ps * (1.0 + t * 2.5))
        c = apply_tint(QColor(*SMOKE_COLOR), tint)
        c.setAlpha(int(45 * (1.0 - t) * fade))
        painter.fillRect(int(self.x - size // 2), int(self.y), size, size, c)


class Campfire:
    """One campfire: stones, logs, heat-sim flame, sparks, smoke, glow, campers"""

    GRID_W = 15   # heat grid width in cells (odd)
    GRID_H = 22   # heat grid height in cells
    FLAME_H = 16  # typical visual flame height (for glow / smoke placement)
    SIM_EVERY = 3  # run the heat sim every N frames (~30Hz at 90fps)

    def __init__(self, x, rng, ps, area_height, depth=0.0, camper_specs=None,
                 tent_side=None, tent_kind=None):
        self.x = x  # center x (widget px)
        self.ps = ps
        self.depth = depth   # 0 = front, 1 = far (drawn smaller)
        # Atmospheric haze: distant fires shift toward blue (like far mountains)
        self.haze = 0.38 * depth
        # List of (spec, mirror, seat_offset): mirror=1 left / -1 right side,
        # seat_offset = extra cells away from the fire (second row of seats)
        self.camper_specs = camper_specs or [(make_camper_spec("warm", 0), 1, 0),
                                             (make_camper_spec("marshmallow", 1), -1, 0)]
        self.rng = rng
        self._base_y = area_height - 4 * ps  # refined in draw via set_base_y
        self._wind = 0.0
        self.noise = PinkNoiseGenerator()
        self.level = 0.0       # smoothed flame intensity (-1..1), 1/f yuragi
        self.frame = rng.randint(0, 1000)
        self.sparks = []
        self.smoke = []
        # Per-fire desync so multiple fires don't flicker in unison
        self.phase = rng.uniform(0, math.tau)
        # Tent on a random side of the fire, in a random canvas color.
        # Sometimes a glamping bell tent (bigger, cream canvas) instead.
        self.tent_side = tent_side if tent_side is not None else rng.choice([-1, 1])
        self.tent_kind = tent_kind if tent_kind is not None else rng.choice(["aframe", "aframe", "bell"])
        self.tent_color = BELL_TENT_COLOR if self.tent_kind == "bell" else rng.choice(TENT_COLORS)
        # Garland rigging: strung from the tent peak or between two poles,
        # sometimes continuing from the pole down to a ground stake
        self.garland_style = rng.choice(["tent", "poles"])
        self.fire_on = True
        self.ambient = 0.30  # base brightness for campers/tent (set by scene)
        # Heat grid: heat[y][x], y=0 at the base
        self.heat = [[0.0] * self.GRID_W for _ in range(self.GRID_H)]
        # Per-column 1/f noise modulating the heat injection
        self.col_noise = [PinkNoiseGenerator() for _ in range(self.GRID_W)]
        self.col_inj = [0.0] * self.GRID_W

    def _tinted(self, color, tint):
        """apply_tint + blue atmospheric haze proportional to depth"""
        c = apply_tint(color, tint)
        k = self.haze
        if k > 0:
            c = QColor(
                int(c.red() * (1 - k) + HAZE_COLOR[0] * k),
                int(c.green() * (1 - k) + HAZE_COLOR[1] * k),
                int(c.blue() * (1 - k) + HAZE_COLOR[2] * k),
            )
        return c

    def _step_heat(self, wind):
        """One step of the fire propagation: inject at base, advect upward
        with wind drift, decay randomly. The silhouette emerges naturally."""
        W, H = self.GRID_W, self.GRID_H
        rng = self.rng
        half = (W - 1) / 2.0
        flicker = 0.82 + 0.28 * self.level

        # Inject heat at the base: bell envelope * per-column 1/f yuragi
        # (when the fire is out, injection stops and the flame dies naturally)
        for x in range(W):
            d = abs(x - half) / half  # 0 center .. 1 edge
            env = max(0.0, 1.0 - d * d * 2.2)  # narrower than the grid
            self.col_inj[x] += (self.col_noise[x].next() - self.col_inj[x]) * 0.3
            inj = env * flicker * (0.95 + 0.25 * self.col_inj[x]) if self.fire_on else 0.0
            self.heat[0][x] = max(0.0, min(1.0, inj))

        # Wind bias: probability of taking heat from the upwind cell
        wb = max(-0.18, min(0.18, wind * 0.15))
        # Propagate upward (top-down so each row reads last step's values below)
        for y in range(H - 1, 0, -1):
            row = self.heat[y]
            below = self.heat[y - 1]
            for x in range(W):
                r = rng.random()
                if r < 0.2 + wb:
                    sx = x - 1  # heat comes from the left -> flame leans right
                elif r > 0.8 + wb:
                    sx = x + 1
                else:
                    sx = x
                if 0 <= sx < W:
                    # Decay: random + extra at the sides (keeps the flame slim)
                    d = abs(x - half) / half
                    h = below[sx] - (0.012 + rng.random() * 0.06 + d * 0.05)
                    row[x] = h if h > 0.0 else 0.0
                else:
                    row[x] = 0.0

    def update(self, wind, spark_amount, smoke_on):
        self.frame += 1
        # 1/f flicker, smoothed
        self.level += (self.noise.next() - self.level) * 0.15
        if self.frame % self.SIM_EVERY == 0:
            self._step_heat(wind)
        # Spawn sparks from flame area
        if self.fire_on and spark_amount > 0 and self.rng.random() < spark_amount / 100.0 * 0.35:
            sx = self.x + self.rng.uniform(-2, 2) * self.ps
            sy = self._base_y - self.rng.uniform(4, 10) * self.ps
            self.sparks.append(Spark(sx, sy, self.rng, self.ps))
        # Extinguished fire: only thin wisps of smoke from the embers
        smoke_interval = 18 if self.fire_on else 42
        if smoke_on and self.frame % smoke_interval == 0:
            sx = self.x + self.rng.uniform(-1.5, 1.5) * self.ps
            rise = self.FLAME_H * 0.9 if self.fire_on else 2
            sy = self._base_y - rise * self.ps
            self.smoke.append(Smoke(sx, sy, self.rng, self.ps))
        for s in self.sparks:
            s.update(wind)
        for s in self.smoke:
            s.update(wind)
        self.sparks = [s for s in self.sparks if s.alive and s.y > -20]
        self.smoke = [s for s in self.smoke if s.alive and s.y > -30]
        self._wind = wind

    def set_base_y(self, ground_y):
        self._base_y = ground_y - 4 * self.ps  # flame sits on top of logs

    def _draw_camper(self, painter, ground_y, variant, mirror, seat_offset, tint, fade):
        """Camper sitting by the fire. mirror=1: left side (facing right),
        mirror=-1: right side (facing left). Fire-facing pixels are lit red
        and flicker with the fire; the back fades into darkness."""
        ps = self.ps
        # back-side origin (dx grows toward fire); outer seats sit further away
        anchor = self.x - mirror * (18 + seat_offset) * ps
        palette = variant["palette"]
        # Firelight flicker on the body (follows the fire's 1/f level)
        if self.fire_on:
            flick = max(0.0, min(1.0, 0.78 + 0.22 * self.level
                                 + 0.08 * math.sin(self.frame * 0.27 + self.phase + mirror)))
        else:
            flick = 0.0
        for dx, dy, part in variant["cells"]:
            base = palette[part]
            # Lighting: ambient (moonlight/twilight) + firelight on the front
            norm = max(0.0, min(1.0, (dx / _CAMPER_SPAN - 0.3) / 0.7))
            # Outer seats are further from the fire -> weaker firelight
            glow = norm * flick / (1.0 + seat_offset * 0.05)
            bright = self.ambient + 0.70 * glow
            c = QColor(
                min(255, int(base[0] * bright + 70 * glow)),
                min(255, int(base[1] * bright + 26 * glow)),
                min(255, int(base[2] * bright + 6 * glow)),
            )
            c = self._tinted(c, tint)
            c.setAlpha(int(255 * fade))
            px = int(anchor + mirror * dx * ps)
            py = int(ground_y - (dy + 1) * ps)
            painter.fillRect(px, py, ps, ps, c)

    TENT_H = 11       # tent height in cells
    TENT_HALF_W = 9   # tent base half-width in cells
    TENT_DOOR = (24, 20, 30)       # dark entrance

    def _draw_tent(self, painter, ground_y, tint, fade):
        """Tent beside the fire. The fire-facing slope is lit warm, the far
        side fades into the night. Entrance faces the fire.
        aframe: triangular tent  bell: bigger glamping tent (rounded walls)"""
        if self.tent_kind == "cabin":
            self._draw_cabin(painter, ground_y, tint, fade)
            return
        ps = self.ps
        side = self.tent_side
        cx = self.x + side * 38 * ps  # tent center
        bell = self.tent_kind == "bell"
        if bell:
            H, HW = self.TENT_H + 4, self.TENT_HALF_W + 4
        else:
            H, HW = self.TENT_H, self.TENT_HALF_W
        if self.fire_on:
            flick = max(0.0, min(1.0, 0.75 + 0.25 * self.level
                                 + 0.06 * math.sin(self.frame * 0.23 + self.phase)))
        else:
            flick = 0.0
        for j in range(H):
            if bell:
                # Bell tent: near-vertical canvas walls, conical top
                half_w = round(HW * (1.0 - (j / H) ** 2.2))
            else:
                half_w = round(HW * (1.0 - j / H))
            py = int(ground_y - (j + 1) * ps)
            for dxc in range(-half_w, half_w + 1):
                # Entrance: dark opening on the fire-facing slope, near the ground
                toward_fire = dxc * -side  # positive = fire side
                if j < (6 if bell else 5) and toward_fire > half_w - 3:
                    base = self.TENT_DOOR
                else:
                    base = self.tent_color
                # Firelight: fire-facing side lit, far side dark
                u = (toward_fire + HW) / (2.0 * HW)  # 0 far .. 1 fire side
                glow = (u ** 1.6) * flick
                bright = self.ambient + 0.78 * glow
                c = QColor(
                    min(255, int(base[0] * bright + 70 * glow)),
                    min(255, int(base[1] * bright + 26 * glow)),
                    min(255, int(base[2] * bright + 6 * glow)),
                )
                c = self._tinted(c, tint)
                c.setAlpha(int(255 * fade))
                painter.fillRect(int(cx + dxc * ps), py, ps, ps, c)

    CABIN_WALL = (150, 108, 68)
    CABIN_WALL_DARK = (124, 88, 54)
    CABIN_ROOF = (88, 66, 52)
    CABIN_DOOR = (60, 42, 30)
    CABIN_WINDOW_LIT = (255, 205, 110)
    CABIN_WINDOW_DARK = (38, 44, 58)

    def _draw_cabin(self, painter, ground_y, tint, fade):
        """Glamping cottage: log walls, gable roof, door facing the fire and
        a window that glows warm in the evening/night."""
        ps = self.ps
        side = self.tent_side
        cx = self.x + side * 38 * ps
        HW = 10      # half width in cells
        WALL_H = 8
        ROOF_H = 6
        if self.fire_on:
            flick = max(0.0, min(1.0, 0.75 + 0.25 * self.level
                                 + 0.06 * math.sin(self.frame * 0.23 + self.phase)))
        else:
            flick = 0.0
        window_lit = self.ambient <= 0.55

        def paint(base, dxc, py, full_bright=False):
            toward_fire = dxc * -side
            u = max(0.0, min(1.0, (toward_fire + HW) / (2.0 * HW)))
            glow = (u ** 1.6) * flick
            bright = 1.0 if full_bright else self.ambient + 0.78 * glow
            c = QColor(
                min(255, int(base[0] * bright + 70 * glow)),
                min(255, int(base[1] * bright + 26 * glow)),
                min(255, int(base[2] * bright + 6 * glow)),
            )
            c = self._tinted(c, tint)
            c.setAlpha(int(255 * fade))
            painter.fillRect(int(cx + dxc * ps), py, ps, ps, c)

        # Log walls (alternating stripes), door on the fire side, window opposite
        for j in range(WALL_H):
            py = int(ground_y - (j + 1) * ps)
            for dxc in range(-HW, HW + 1):
                toward_fire = dxc * -side
                if j < 5 and toward_fire > HW - 4:
                    paint(self.CABIN_DOOR, dxc, py)
                elif 3 <= j <= 5 and -3 <= toward_fire <= 0:
                    base = self.CABIN_WINDOW_LIT if window_lit else self.CABIN_WINDOW_DARK
                    paint(base, dxc, py, full_bright=window_lit)
                else:
                    base = self.CABIN_WALL if j % 2 == 0 else self.CABIN_WALL_DARK
                    paint(base, dxc, py)
        # Gable roof with overhang
        for j in range(ROOF_H):
            half = round((HW + 2) * (1.0 - j / ROOF_H))
            py = int(ground_y - (WALL_H + j + 1) * ps)
            for dxc in range(-half, half + 1):
                paint(self.CABIN_ROOF, dxc, py)

    def _draw_garland(self, painter, ground_y, tint, fade):
        """Glamping string of colorful LED ball lights, strung high across
        the campsite like a line crossing a schoolyard. Styles:
          tent:  tent peak -> pole on the far side of the fire
          poles: two poles, one on each side (free-standing rig)
        The string continues from the pole down to a ground stake."""
        ps = self.ps
        side = self.tent_side
        H = self.TENT_H + 4  # bell tent height = garland height
        top_y = ground_y - (H + 1) * ps
        night = self.ambient <= 0.35

        def draw_pole(px):
            c = self._tinted(QColor(82, 66, 50), tint)
            c.setAlpha(int(255 * fade))
            painter.fillRect(int(px), int(top_y), ps, int(ground_y - top_y), c)

        ax = self.x + side * 38 * ps  # anchor on the tent side
        bx = self.x - side * 38 * ps  # anchor opposite the tent
        draw_pole(bx)
        if self.garland_style == "poles":
            ax = self.x + side * 34 * ps  # own pole, standing clear of the tent
            draw_pole(ax)

        def draw_bulb(fx, fy, k):
            col = LED_COLORS[k % len(LED_COLORS)]
            if night:
                # Self-luminous, gently twinkling
                tw = 0.7 + 0.3 * math.sin(self.frame * 0.06 + k * 1.9 + self.phase)
                lc = self._tinted(QColor(*col), tint)
                lc.setAlpha(int(245 * tw * fade))
            else:
                # Daytime: unlit plastic balls, dimmed by ambient light
                lc = self._tinted(QColor(int(col[0] * self.ambient),
                                         int(col[1] * self.ambient),
                                         int(col[2] * self.ambient)), tint)
                lc.setAlpha(int(255 * fade))
            painter.fillRect(int(fx), int(fy), ps, ps, lc)

        # Gentle sway of the hanging string (strongest mid-span, ends fixed)
        sway = (math.sin(self.frame * 0.030 + self.phase)
                + 0.5 * math.sin(self.frame * 0.011 + self.phase * 2))

        def draw_span(x0, y0, x1, y1, n, sag, k0):
            def pos(t):
                dip = math.sin(math.pi * t)
                return (x0 + (x1 - x0) * t + sway * dip * 0.9 * ps,
                        y0 + (y1 - y0) * t + dip * sag * ps
                        + 0.25 * ps * dip * math.sin(self.frame * 0.045 + self.phase))
            for k in range(n):
                fx, fy = pos((k + 0.5) / n)
                draw_bulb(fx, fy, k0 + k)

        # Main span across the campsite, over the fire
        draw_span(ax, top_y, bx, top_y, 13, 5, 0)
        # Tail: the string always continues from the pole down to a ground stake
        tx = bx - side * 10 * ps  # away from the fire
        draw_span(bx, top_y, tx, ground_y - 2 * ps, 4, 1.5, 13)

    def draw(self, painter, ground_y, tint, fade, glow_on, smoke_on, campers_on, tents_on):
        ps = self.ps
        self.set_base_y(ground_y)
        base_y = self._base_y
        flicker = 0.85 + 0.25 * self.level + 0.05 * math.sin(self.frame * 0.21 + self.phase)

        # --- Glow (behind everything) ---
        if glow_on and self.fire_on:
            radius = (self.FLAME_H + 8) * ps * (0.9 + 0.15 * self.level)
            grad = QRadialGradient(self.x, base_y - 4 * ps, radius)
            gc = self._tinted(QColor(255, 140, 40), tint)
            gc.setAlpha(int(38 * flicker * fade))
            grad.setColorAt(0.0, gc)
            gc2 = QColor(gc)
            gc2.setAlpha(0)
            grad.setColorAt(1.0, gc2)
            painter.fillRect(int(self.x - radius), int(base_y - 4 * ps - radius),
                             int(radius * 2), int(radius * 2), grad)

        # --- Smoke (behind flame) ---
        if smoke_on:
            for s in self.smoke:
                s.draw(painter, tint, fade)

        # --- Tent (behind campers, further from the fire) ---
        if tents_on:
            self._draw_tent(painter, ground_y, tint, fade)
            # Glamping sites get a garland strung across the camp
            if self.tent_kind in ("bell", "cabin"):
                self._draw_garland(painter, ground_y, tint, fade)

        # --- Campers (beside the fire) ---
        if campers_on:
            for spec, mirror, seat_offset in self.camper_specs:
                self._draw_camper(painter, ground_y, spec, mirror, seat_offset, tint, fade)

        # --- Stones ring ---
        stone_y = ground_y - ps
        half_w = 7 * ps
        for i, sx in enumerate(range(-half_w, half_w + 1, 2 * ps)):
            c = STONE_DARK if i % 2 else STONE_COLOR
            c = self._tinted(c, tint)
            c.setAlpha(int(255 * fade))
            painter.fillRect(int(self.x + sx - ps), stone_y - ps, 2 * ps, 2 * ps, c)

        # --- Logs (crossed) ---
        log_y = ground_y - 3 * ps
        for c, rect in (
            (LOG_DARK, (-5, 0, 10, 2)),   # back log
            (LOG_COLOR, (-4, 1, 9, 2)),   # front log (slightly offset)
        ):
            lx, ly, lw, lh = rect
            col = self._tinted(c, tint)
            col.setAlpha(int(255 * fade))
            painter.fillRect(int(self.x + lx * ps), log_y + ly * ps, lw * ps, lh * ps, col)
        # Log ends
        end = self._tinted(LOG_END, tint)
        end.setAlpha(int(255 * fade))
        painter.fillRect(int(self.x - 5 * ps), log_y, ps, 2 * ps, end)
        painter.fillRect(int(self.x + 4 * ps), log_y + ps, ps, 2 * ps, end)

        # --- Embers (extinguished fire: faint pulsing glow between the logs) ---
        if not self.fire_on:
            for i, (ex, ey) in enumerate(((-2, 0), (0, 1), (1, 0), (3, 1), (-3, 1))):
                pulse = 0.5 + 0.5 * math.sin(self.frame * 0.05 + self.phase + i * 1.7)
                c = QColor(170, 55, 20) if i % 2 else QColor(120, 35, 15)
                c = self._tinted(c, tint)
                c.setAlpha(int((60 + 130 * pulse) * fade))
                painter.fillRect(int(self.x + ex * ps), log_y + ey * ps, ps, ps, c)

        # --- Flame (heat grid -> color bands) ---
        bands = []
        for thr, color, alpha in HEAT_BANDS:
            c = self._tinted(color, tint)
            c.setAlpha(int(alpha * fade))
            bands.append((thr, c))
        half = (self.GRID_W - 1) / 2.0
        x0 = self.x - half * ps
        for y in range(self.GRID_H):
            row = self.heat[y]
            py = int(base_y - (y + 1) * ps)
            for gx in range(self.GRID_W):
                h = row[gx]
                if h < 0.06:
                    continue
                for thr, c in bands:
                    if h >= thr:
                        painter.fillRect(int(x0 + gx * ps), py, ps, ps, c)
                        break

        # --- Sparks (in front of flame) ---
        for s in self.sparks:
            s.draw(painter, tint, fade)


class TakibiScene(BaseScene):
    """Campfire scene: one or more campfires flickering with 1/f yuragi"""

    def __init__(self):
        self.fires = []
        self.widget_width = 0
        self.area_height = 140
        self.scale = 1.0
        self.ps = PIXEL_SIZE
        self.spark_amount = 25
        self.smoke_on = True
        self.glow_on = True
        self.campers_on = True
        self.tents_on = True
        self._config = None
        self.phase = "night"
        self._phase_tick = 0

    def _resolve_phase(self):
        """Map the global lighting mode to a campfire phase."""
        mode = self._config.get("lighting_mode", "off") if self._config else "off"
        if mode == "auto":
            now = datetime.datetime.now()
            h = now.hour + now.minute / 60.0
            if 2 <= h < 4:
                return "deepnight"   # everyone asleep
            if 4 <= h < 7:
                return "dawn"        # fire is out, first light
            if 7 <= h < 17:
                return "day"
            if 17 <= h < 20:
                return "evening"
            return "night"           # 20:00 - 02:00
        return {"sunrise": "dawn", "daytime": "day",
                "sunset": "evening", "night": "night"}.get(mode, "night")

    def _apply_phase(self, phase):
        self.phase = phase
        p = PHASES[phase]
        for f in self.fires:
            f.fire_on = p["fire"]
            f.ambient = p["ambient"]

    def get_area_height(self, config):
        s = config.get("takibi_scale", 100) / 100.0
        return int(140 * s)

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("takibi_scale", 100) / 100.0
        self.ps = max(1, int(PIXEL_SIZE * self.scale))
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)
        self.spark_amount = config.get("takibi_sparks", 25)
        self.smoke_on = config.get("takibi_smoke", True)
        self.glow_on = config.get("takibi_glow", True)
        self.campers_on = config.get("takibi_campers", True)
        self.tents_on = config.get("takibi_tents", True)
        self._config = config  # live reference; lighting_mode may change in place
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed)

        count = max(1, config.get("takibi_count", 1))
        # Every camper in the whole campsite is a different person:
        # shuffle all (pose, palette) combos and hand them out in order
        combos = [(pose, pi) for pose in CAMPER_POSES for pi in range(len(CAMPER_PALETTES))]
        rng.shuffle(combos)
        # Depths: spread evenly from front (0) to far (1), shuffled so the
        # campsite looks like it's seen from one viewpoint on the meadow
        if count == 1:
            depths = [0.0]
        else:
            depths = [i / (count - 1) for i in range(count)]
            rng.shuffle(depths)
        self.fires = []
        combo_i = 0
        for i in range(count):
            # Spread evenly; single fire goes to center
            x = widget_width * (i + 1) / (count + 1)
            x += rng.uniform(-0.05, 0.05) * widget_width / count
            depth = depths[i]
            # Perspective: farther fires are drawn smaller
            f_ps = max(1, round(self.ps * (1.0 - 0.45 * depth)))
            # Tent decided here so the group size can match the site:
            # glamping sites (bell tent / cottage) are lively with many people
            tent_side = rng.choice([-1, 1])
            tent_kind = rng.choice(["aframe", "aframe", "bell", "cabin"])
            if tent_kind in ("bell", "cabin"):
                n = rng.choice([4, 5, 5, 6])
            else:
                n = rng.choice([1, 2, 2, 2, 3, 3, 4])
            # Seats: inner left/right, a second row further out, and a third
            # row on the side away from the tent
            away = -tent_side
            seats = [(1, 0), (-1, 0), (-1, 9), (1, 9), (away, 18), (away, 27)]
            if n == 1:
                seats = [(rng.choice([-1, 1]), 0)]
            specs = []
            for mirror, seat_offset in seats[:n]:
                pose, pal = combos[combo_i % len(combos)]
                combo_i += 1
                specs.append((make_camper_spec(pose, pal), mirror, seat_offset))
            self.fires.append(Campfire(x, random.Random(rng.randint(0, 999999)),
                                       f_ps, self.area_height, depth, specs,
                                       tent_side, tent_kind))
        # Draw back to front
        self.fires.sort(key=lambda f: -f.depth)

        self._apply_phase(self._resolve_phase())

    def update(self, wind_sim, mouse_pos=None):
        # Re-check the time-of-day phase about once a second
        self._phase_tick += 1
        if self._phase_tick >= 90:
            self._phase_tick = 0
            phase = self._resolve_phase()
            if phase != self.phase:
                self._apply_phase(phase)
        for f in self.fires:
            wind = wind_sim.get_wave_at(f.x)
            f.update(wind, self.spark_amount, self.smoke_on)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        # The campfire is its own light source: ignore the global tint and
        # let the phase (PHASES) drive the mood instead.
        ph = PHASES[self.phase]
        campers_on = self.campers_on and ph["campers"]
        for f in self.fires:
            alpha = get_alpha(f.x) if get_alpha else 255
            if alpha <= 0:
                continue
            f.draw(painter, ground_y, None, alpha / 255.0,
                   self.glow_on, self.smoke_on, campers_on, self.tents_on)
