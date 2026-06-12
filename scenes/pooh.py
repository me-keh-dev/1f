"""Pooh scene - Pooh floating with a blue balloon over the 100 Acre Wood"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QLinearGradient


# --- Pooh pixel art (classic style, hanging from balloon string) ---
# (dx, dy, part) relative to center. dy positive = up
POOH_BODY = [
    # Head
    (-1, 7, 'ear'), (2, 7, 'ear'),
    (0, 8, 'head'), (1, 8, 'head'),
    (-1, 8, 'head'), (2, 8, 'head'),
    (0, 7, 'head'), (1, 7, 'head'),
    (0, 6, 'head'), (1, 6, 'head'),
    # Eyes + nose
    (0, 7, 'eye'), (1, 7, 'eye'),
    (0, 6, 'nose'),
    # Body (no shirt - original 1926 Pooh)
    (-1, 5, 'body'), (0, 5, 'body'), (1, 5, 'body'), (2, 5, 'body'),
    (-1, 4, 'body'), (0, 4, 'body'), (1, 4, 'body'), (2, 4, 'body'),
    (0, 3, 'tummy'), (1, 3, 'tummy'),
    (-1, 3, 'body'), (2, 3, 'body'),
    (0, 2, 'body'), (1, 2, 'body'),
    # Arms (reaching up for string)
    (-2, 6, 'body'), (-2, 7, 'body'), (-2, 8, 'body'),
    (3, 6, 'body'), (3, 7, 'body'), (3, 8, 'body'),
    # Legs (dangling)
    (-1, 1, 'body'), (0, 1, 'body'),
    (1, 1, 'body'), (2, 1, 'body'),
    (-1, 0, 'foot'), (2, 0, 'foot'),
]

POOH_COLORS = {
    'head': (210, 175, 75),
    'ear': (190, 155, 55),
    'eye': (30, 30, 30),
    'nose': (50, 40, 30),
    'body': (210, 175, 75),
    'tummy': (225, 195, 100),
    'foot': (190, 155, 55),
}

# --- Blue balloon ---
# Circle radius 3 → 7x7 pixels, centered at (0, 4)
BALLOON_PIXELS = []
_BR = 3
_BCX, _BCY = 0, 4
for _by in range(-_BR, _BR + 1):
    for _bx in range(-_BR, _BR + 1):
        if _bx * _bx + _by * _by <= _BR * _BR:
            _part = 'highlight' if (_bx <= -1 and _by >= 1) else 'balloon'
            BALLOON_PIXELS.append((_bx + _BCX, _by + _BCY, _part))
BALLOON_PIXELS.append((_BCX, _BCY - _BR - 1, 'knot'))

BALLOON_COLORS = {
    'balloon': (70, 130, 210),
    'highlight': (140, 185, 240),
    'knot': (50, 100, 180),
}

# --- Miniature forest elements ---
MINI_TREE_VARIANTS = [
    # Small oak
    [(0, 3, 'trunk'), (0, 2, 'trunk'), (-1, 4, 'leaf'), (0, 4, 'leaf'), (1, 4, 'leaf'),
     (-1, 5, 'leaf'), (0, 5, 'leaf'), (1, 5, 'leaf'), (0, 6, 'leaf')],
    # Bushy tree
    [(0, 2, 'trunk'), (0, 1, 'trunk'), (-1, 3, 'leaf'), (0, 3, 'leaf'), (1, 3, 'leaf'),
     (-2, 4, 'leaf'), (-1, 4, 'leaf'), (0, 4, 'leaf'), (1, 4, 'leaf'), (2, 4, 'leaf'),
     (-1, 5, 'leaf'), (0, 5, 'leaf'), (1, 5, 'leaf')],
    # Tall thin
    [(0, 2, 'trunk'), (0, 3, 'trunk'), (0, 4, 'trunk'),
     (-1, 5, 'leaf'), (0, 5, 'leaf'), (1, 5, 'leaf'),
     (0, 6, 'leaf'), (0, 7, 'leaf')],
]

FOREST_COLORS = {
    'trunk': (100, 70, 40),
    'leaf': (60, 120, 50),
    'leaf_light': (80, 150, 65),
    'house_wall': (180, 160, 120),
    'house_roof': (120, 80, 40),
    'house_door': (90, 60, 30),
    'bridge': (140, 110, 70),
    'water': (100, 160, 210),
}

# Tiny house
MINI_HOUSE = [
    (0, 1, 'house_door'),
    (-1, 1, 'house_wall'), (1, 1, 'house_wall'),
    (-1, 2, 'house_wall'), (0, 2, 'house_wall'), (1, 2, 'house_wall'),
    (-2, 3, 'house_roof'), (-1, 3, 'house_roof'), (0, 3, 'house_roof'),
    (1, 3, 'house_roof'), (2, 3, 'house_roof'),
    (-1, 4, 'house_roof'), (0, 4, 'house_roof'), (1, 4, 'house_roof'),
]

# Bridge
MINI_BRIDGE = [
    (-2, 1, 'bridge'), (-1, 1, 'bridge'), (0, 1, 'bridge'), (1, 1, 'bridge'), (2, 1, 'bridge'),
    (-3, 2, 'bridge'), (3, 2, 'bridge'),
    (-3, 0, 'water'), (-2, 0, 'water'), (-1, 0, 'water'),
    (0, 0, 'water'), (1, 0, 'water'), (2, 0, 'water'), (3, 0, 'water'),
]

# Christopher Robin (tiny, 3x5 pixels)
CR_FRAMES = [
    [(-1, 4, 'umbrella'), (0, 4, 'umbrella'), (1, 4, 'umbrella'),
     (0, 3, 'head'), (0, 2, 'body'), (0, 1, 'legs'), (-1, 0, 'legs')],
    [(-1, 4, 'umbrella'), (0, 4, 'umbrella'), (1, 4, 'umbrella'),
     (0, 3, 'head'), (0, 2, 'body'), (-1, 1, 'legs'), (0, 0, 'legs')],
]
CR_COLORS = {
    'umbrella': (70, 120, 200),
    'head': (220, 190, 150),
    'body': (60, 80, 130),
    'legs': (80, 70, 50),
}


# --- Tigger (arc jump across screen — appears from one side, lands on other) ---
class Tigger:
    def __init__(self, x, area_height, rng):
        self.area_height = area_height
        self.screen_width = 1920
        self.noise = PinkNoiseGenerator()
        self.visible = False
        self.wait_timer = random.randint(270, 540)  # 3-6 seconds at 90fps
        self.bounces_left = 0
        self.ground_below = 40  # invisible ground below screen
        self.x = 0.0
        self.y = self.ground_below
        self.vx = 0.0
        self.vy = 0.0
        self.gravity = 0.08

    def _start_sequence(self):
        # Start a bouncing sequence from one side to the other
        from_left = random.random() < 0.5
        self.direction = 1 if from_left else -1
        self.x = -30.0 if from_left else self.screen_width + 30.0
        self.vx = self.direction * random.uniform(1.5, 2.5)
        self.bounces_left = random.randint(3, 6)  # number of bounces across screen
        self._do_bounce()

    def _do_bounce(self):
        # y starts at ground_below (positive = below screen)
        self.y = self.ground_below
        self.vy = -random.uniform(3.5, 4.5)  # moderate jump — peaks below Pooh's feet
        self.visible = True

    def update(self):
        if not self.visible:
            self.x += self.vx * 1.5  # running on ground
            self.wait_timer -= 1
            if self.wait_timer <= 0:
                if self.bounces_left > 0:
                    self._do_bounce()  # next bounce in sequence
                else:
                    self._start_sequence()  # new sequence
            return
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        # Fell back below ground → bounce again or finish
        if self.y >= self.ground_below and self.vy > 0:
            self.y = self.ground_below
            self.bounces_left -= 1
            # Every landing → wait 3 seconds before next jump
            self.visible = False
            self.wait_timer = 270  # ~3 seconds at 90fps
            if self.bounces_left <= 0:
                self.wait_timer = random.randint(270, 540)

    def draw(self, painter, ground_y, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush
        if not self.visible:
            return
        u = ps
        cx = self.x
        # ground_y is bottom of visible area; y=0 is top
        cy = ground_y + self.y
        # Only draw if visible on screen
        if cy > ground_y + u * 5:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        # Classic Tigger: muted caramel orange, no white belly
        orange = QColor(190, 130, 50)  # antique/muted orange
        stripe = QColor(60, 40, 20)    # dark brown stripes (not black)
        if tint:
            orange = apply_tint(orange, tint)
            stripe = apply_tint(stripe, tint)

        # Body (round, toylike, stuffed animal proportions)
        body = QPainterPath()
        body.addEllipse(cx - u * 1.5, cy - u * 2, u * 3, u * 3.5)
        painter.fillPath(body, QBrush(orange))
        # Stripes across entire body (no belly separation)
        for sy in range(-2, 3):
            for sdx in [-1, 1]:
                sp = QPainterPath()
                sp.addEllipse(cx + sdx * u * 0.9, cy + sy * u * 0.7 - u * 0.1, u * 0.6, u * 0.25)
                painter.fillPath(sp, QBrush(stripe))
        # Head (round, chubby)
        head = QPainterPath()
        head.addEllipse(cx - u * 1.3, cy - u * 3.8, u * 2.6, u * 2.2)
        painter.fillPath(head, QBrush(orange))
        # Head stripes
        for hdx in [-0.8, 0.8]:
            hs = QPainterPath()
            hs.addEllipse(cx + hdx * u, cy - u * 3.3, u * 0.4, u * 0.2)
            painter.fillPath(hs, QBrush(stripe))
        # Ears (small, round)
        for edx in [-u * 1.0, u * 1.0]:
            ep = QPainterPath()
            ep.addEllipse(cx + edx - u * 0.3, cy - u * 4.0, u * 0.6, u * 0.6)
            painter.fillPath(ep, QBrush(orange))
        # Eyes + nose (brown outlines, not black)
        painter.setBrush(QBrush(stripe))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - u * 0.5), int(cy - u * 3.0), int(u * 0.35), int(u * 0.35))
        painter.drawEllipse(int(cx + u * 0.3), int(cy - u * 3.0), int(u * 0.35), int(u * 0.35))
        painter.drawEllipse(int(cx - u * 0.1), int(cy - u * 2.5), int(u * 0.3), int(u * 0.25))
        # Limbs (jumping pose — four legs spread)
        for lx, ly, angle in [(-u*1.8, cy-u*0.5, -30), (u*1.8, cy-u*0.5, 30),
                                (-u*1.3, cy+u*1.2, -15), (u*1.3, cy+u*1.2, 15)]:
            lp = QPainterPath()
            lp.addEllipse(cx + lx - u*0.3, ly, u*0.7, u*1.2)
            painter.fillPath(lp, QBrush(orange))
        # Tail (simple, not spring — just a curved stripe tail)
        tp = QPainterPath()
        tp.addEllipse(cx - u * 0.2, cy + u * 1.3, u * 0.4, u * 1.5)
        painter.fillPath(tp, QBrush(orange))
        ts = QPainterPath()
        ts.addEllipse(cx - u * 0.15, cy + u * 2.0, u * 0.3, u * 0.3)
        painter.fillPath(ts, QBrush(stripe))
        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing, False)


# --- Eeyore (floating with balloon, looking sad) ---
class Eeyore:
    def __init__(self, x, y, rng):
        self.x = float(x)
        self.y = float(y)
        self.base_y = float(y)
        self.noise_x = PinkNoiseGenerator()
        self.noise_y = PinkNoiseGenerator()
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.swing_angle = 0.0
        self.swing_vel = 0.0
        self._prev_vx = 0.0

    def update(self, mouse_pos=None):
        nx = self.noise_x.next()
        ny = self.noise_y.next()
        self.vel_x += nx * 0.005
        self.vel_y += (self.base_y + ny * 5 - self.y) * 0.001
        if mouse_pos:
            mx, my = mouse_pos
            dx = self.x - mx
            dy = self.y - my
            dist = max(10, math.sqrt(dx * dx + dy * dy))
            if dist < 150:
                force = (150 - dist) / 150 * 0.12
                self.vel_x += (dx / dist) * force
                self.vel_y += (dy / dist) * force * 0.3
        self.vel_x *= 0.997
        self.vel_y *= 0.995
        accel_x = self.vel_x - self._prev_vx
        self._prev_vx = self.vel_x
        if abs(accel_x) > 0.02:
            self.swing_vel += accel_x * 0.4
        self.swing_vel -= math.sin(self.swing_angle) * 0.012
        self.swing_vel *= 0.98
        self.swing_angle += self.swing_vel
        self.swing_angle = max(-0.4, min(0.4, self.swing_angle))
        self.x += self.vel_x
        self.y += self.vel_y
        self.y = max(40, self.y)

    def draw(self, painter, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush, QRadialGradient
        u = ps
        cx, cy = self.x, self.y

        painter.setRenderHint(QPainter.Antialiasing, True)
        grey = QColor(140, 140, 155)
        dark_grey = QColor(100, 100, 115)
        pink = QColor(200, 160, 170)
        if tint:
            grey = apply_tint(grey, tint)
            dark_grey = apply_tint(dark_grey, tint)
            pink = apply_tint(pink, tint)

        # Balloon (NOT rotated — stays upright)
        bl = QPainterPath()
        br = u * 2
        balloon_y = cy - u * 10
        bl.addEllipse(cx - br, balloon_y - br, br * 2, br * 2)
        painter.fillPath(bl, QBrush(pink))

        # Rotate around balloon bottom for string + body
        pivot_y = balloon_y + br
        painter.save()
        painter.translate(cx, pivot_y)
        painter.rotate(math.degrees(self.swing_angle))
        painter.translate(-cx, -pivot_y)

        # String (curved)
        sc = QColor(50, 50, 50, 150)
        string_len = int(u * 8)
        for i in range(string_len):
            t = i / max(1, string_len)
            sx = int(cx + math.sin(t * 2) * u * 0.5)
            sy = int(pivot_y + i)
            painter.fillRect(sx, sy, 1, 1, sc)

        # Body (horizontal donkey, side view)
        body = QPainterPath()
        body.addEllipse(cx - u * 2.5, cy - u * 1.5, u * 5, u * 3)
        painter.fillPath(body, QBrush(grey))
        # Head (drooping forward)
        head = QPainterPath()
        head.addEllipse(cx + u * 2, cy - u * 2.5, u * 2, u * 2.5)
        painter.fillPath(head, QBrush(grey))
        # Ear (droopy)
        ear = QPainterPath()
        ear.moveTo(cx + u * 3, cy - u * 2.5)
        ear.lineTo(cx + u * 3.5, cy - u * 4)
        ear.lineTo(cx + u * 2.5, cy - u * 3)
        ear.closeSubpath()
        painter.fillPath(ear, QBrush(dark_grey))
        # Eye (sad, looking down)
        painter.setBrush(QBrush(QColor(25, 25, 25)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx + u * 3.2), int(cy - u * 1.5), int(u * 0.3), int(u * 0.3))
        # Legs (dangling)
        for lx in [-u * 1.5, -u * 0.3, u * 0.8, u * 1.8]:
            lp = QPainterPath()
            lp.addEllipse(cx + lx, cy + u * 1, u * 0.6, u * 1.5)
            painter.fillPath(lp, QBrush(dark_grey))
        # Tail (small, pinned on)
        painter.fillRect(int(cx - u * 2.5), int(cy - u * 0.5), int(u * 0.8), int(u * 0.3), dark_grey)
        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.restore()


# --- SmallBalloonChar (Piglet / Rabbit — small character floating with balloon) ---
class SmallBalloonChar:
    def __init__(self, x, y, char_type, rng):
        self.x = float(x)
        self.y = float(y)
        self.base_y = float(y)
        self.char_type = char_type
        self.noise_x = PinkNoiseGenerator()
        self.noise_y = PinkNoiseGenerator()
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.swing_angle = 0.0
        self.swing_vel = 0.0
        self._prev_vx = 0.0

    def update(self, mouse_pos=None):
        nx = self.noise_x.next()
        ny = self.noise_y.next()
        self.vel_x += nx * 0.007
        self.vel_y += (self.base_y + ny * 4 - self.y) * 0.001
        if mouse_pos:
            mx, my = mouse_pos
            dx = self.x - mx
            dy = self.y - my
            dist = max(10, math.sqrt(dx * dx + dy * dy))
            if dist < 130:
                force = (130 - dist) / 130 * 0.18
                self.vel_x += (dx / dist) * force
                self.vel_y += (dy / dist) * force * 0.3
        self.vel_x *= 0.997
        self.vel_y *= 0.995
        accel_x = self.vel_x - self._prev_vx
        self._prev_vx = self.vel_x
        if abs(accel_x) > 0.02:
            self.swing_vel += accel_x * 0.6
        self.swing_vel -= math.sin(self.swing_angle) * 0.015
        self.swing_vel *= 0.97
        self.swing_angle += self.swing_vel
        self.swing_angle = max(-0.5, min(0.5, self.swing_angle))
        self.x += self.vel_x
        self.y += self.vel_y
        self.y = max(30, self.y)

    def draw(self, painter, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush
        u = ps
        cx, cy = self.x, self.y

        painter.setRenderHint(QPainter.Antialiasing, True)

        if self.char_type == 'piglet':
            body_c = QColor(230, 190, 190)
            body_dark = QColor(200, 155, 155)
            balloon_c = QColor(180, 220, 130)
        else:
            body_c = QColor(200, 180, 140)
            body_dark = QColor(170, 150, 110)
            balloon_c = QColor(220, 180, 100)
        if tint:
            body_c = apply_tint(body_c, tint)
            body_dark = apply_tint(body_dark, tint)
            balloon_c = apply_tint(balloon_c, tint)

        # Balloon (NOT rotated)
        bl = QPainterPath()
        br = u * 1.8
        balloon_y = cy - u * 7
        bl.addEllipse(cx - br, balloon_y - br, br * 2, br * 2)
        painter.fillPath(bl, QBrush(balloon_c))

        # Rotate string + body around balloon bottom
        pivot_y = balloon_y + br
        painter.save()
        painter.translate(cx, pivot_y)
        painter.rotate(math.degrees(self.swing_angle))
        painter.translate(-cx, -pivot_y)

        # String (curved)
        sc = QColor(50, 50, 50, 150)
        string_len = int(u * 5)
        for i in range(string_len):
            t = i / max(1, string_len)
            sx = int(cx + math.sin(t * 2) * u * 0.4)
            sy = int(pivot_y + i)
            painter.fillRect(sx, sy, 1, 1, sc)

        # Body (tiny)
        body = QPainterPath()
        body.addEllipse(cx - u * 0.8, cy - u * 1.5, u * 1.6, u * 2)
        painter.fillPath(body, QBrush(body_c))
        # Head
        head = QPainterPath()
        head.addEllipse(cx - u * 0.7, cy - u * 2.8, u * 1.4, u * 1.5)
        painter.fillPath(head, QBrush(body_c))
        # Eye
        painter.setBrush(QBrush(QColor(25, 25, 25)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx + u * 0.2), int(cy - u * 2.2), int(u * 0.3), int(u * 0.3))

        if self.char_type == 'rabbit':
            # Long ears
            for edx in [-u * 0.2, u * 0.3]:
                ep = QPainterPath()
                ep.addEllipse(cx + edx, cy - u * 4.5, u * 0.4, u * 1.8)
                painter.fillPath(ep, QBrush(body_c))
        else:
            # Piglet ears (small, round)
            for edx in [-u * 0.6, u * 0.5]:
                ep = QPainterPath()
                ep.addEllipse(cx + edx, cy - u * 3.3, u * 0.5, u * 0.5)
                painter.fillPath(ep, QBrush(body_dark))
            # Snout
            sp = QPainterPath()
            sp.addEllipse(cx + u * 0.2, cy - u * 1.8, u * 0.5, u * 0.4)
            painter.fillPath(sp, QBrush(body_dark))

        # Legs (tiny, dangling)
        for ldx in [-u * 0.4, u * 0.3]:
            lp = QPainterPath()
            lp.addEllipse(cx + ldx, cy + u * 0.3, u * 0.4, u * 0.8)
            painter.fillPath(lp, QBrush(body_dark))

        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.restore()


# --- Owl (flying, night-time) ---
class Owl:
    def __init__(self, x, y, rng):
        self.x = float(x)
        self.y = float(y)
        self.vx = rng.uniform(0.1, 0.3) * rng.choice([-1, 1])
        self.noise = PinkNoiseGenerator()
        self.wing_phase = 0.0

    def update(self):
        n = self.noise.next()
        self.x += self.vx
        self.y += n * 0.3
        self.wing_phase += 0.06

    def draw(self, painter, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush
        u = ps
        cx, cy = self.x, self.y

        painter.setRenderHint(QPainter.Antialiasing, True)
        brown = QColor(120, 90, 60)
        light = QColor(180, 160, 130)
        if tint:
            brown = apply_tint(brown, tint)
            light = apply_tint(light, tint)

        wing_up = math.sin(self.wing_phase) * u * 2
        # Wings
        for wing_dir in [-1, 1]:
            wp = QPainterPath()
            wx = cx + wing_dir * u * 2.5
            wy = cy - wing_up * (0.5 if wing_dir > 0 else 1)
            wp.moveTo(cx, cy - u * 0.5)
            wp.quadTo(wx, wy - u * 2, wx + wing_dir * u * 1.5, wy)
            wp.quadTo(wx, wy + u * 0.5, cx, cy + u * 0.5)
            wp.closeSubpath()
            painter.fillPath(wp, QBrush(brown))
        # Body
        body = QPainterPath()
        body.addEllipse(cx - u * 1, cy - u * 1.5, u * 2, u * 3)
        painter.fillPath(body, QBrush(brown))
        # Face disc
        face = QPainterPath()
        face.addEllipse(cx - u * 0.8, cy - u * 2, u * 1.6, u * 1.5)
        painter.fillPath(face, QBrush(light))
        # Eyes (big, round — owl eyes)
        painter.setBrush(QBrush(QColor(230, 200, 50)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - u * 0.6), int(cy - u * 1.6), int(u * 0.5), int(u * 0.5))
        painter.drawEllipse(int(cx + u * 0.2), int(cy - u * 1.6), int(u * 0.5), int(u * 0.5))
        # Pupils
        painter.setBrush(QBrush(QColor(20, 20, 20)))
        painter.drawEllipse(int(cx - u * 0.45), int(cy - u * 1.45), int(u * 0.25), int(u * 0.25))
        painter.drawEllipse(int(cx + u * 0.35), int(cy - u * 1.45), int(u * 0.25), int(u * 0.25))
        # Beak
        painter.setBrush(QBrush(QColor(180, 140, 50)))
        painter.drawEllipse(int(cx - u * 0.15), int(cy - u * 1.1), int(u * 0.3), int(u * 0.3))
        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing, False)


# --- Bird ---
class Bird:
    def __init__(self, x, y, rng):
        self.x = float(x)
        self.y = float(y)
        self.vx = rng.uniform(0.15, 0.4) * rng.choice([-1, 1])
        self.vy = 0.0
        self.noise = PinkNoiseGenerator()
        self.frame = 0
        self.frame_counter = 0

    def update(self):
        n = self.noise.next()
        self.vy += n * 0.02
        self.vy *= 0.93
        self.x += self.vx
        self.y += self.vy
        self.frame_counter += 1
        if self.frame_counter >= 10:
            self.frame_counter = 0
            self.frame = 1 - self.frame

    def draw(self, painter, ps=None):
        ps = ps or PIXEL_SIZE
        s = max(1, ps // 2)
        bx, by = int(self.x), int(self.y)
        c = QColor(50, 50, 60, 180)
        # Body
        painter.fillRect(bx, by, s, s, c)
        # Wings (flap up/down)
        wy = -s if self.frame == 0 else s
        painter.fillRect(bx - s, by + wy, s, s, c)
        painter.fillRect(bx + s, by + wy, s, s, c)


# --- Christopher Robin walker ---
class ChristopherRobin:
    def __init__(self, x, y, direction, speed):
        self.x = float(x)
        self.y = y
        self.direction = direction
        self.speed = speed
        self.frame = 0
        self.frame_counter = 0

    def update(self, screen_width):
        self.x += self.speed * self.direction
        self.frame_counter += 1
        if self.frame_counter >= 20:
            self.frame_counter = 0
            self.frame = 1 - self.frame
        margin = 30
        if self.x > screen_width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = screen_width + margin

    def draw(self, painter, alpha=255, ps=None):
        ps = ps or PIXEL_SIZE
        s = max(1, ps // 2)  # tiny character
        shape = CR_FRAMES[self.frame]
        for dx, dy, part in shape:
            actual_dx = dx * self.direction
            c = QColor(*CR_COLORS.get(part, (100, 100, 100)))
            c.setAlpha(alpha)
            painter.fillRect(int(self.x + actual_dx * s), int(self.y - dy * s), s, s, c)


# --- Floating Pooh ---
class FloatingPooh:
    def __init__(self, x, y):
        self.base_x = float(x)
        self.base_y = float(y)
        self.x = float(x)
        self.y = float(y)
        self.noise_x = PinkNoiseGenerator()
        self.noise_y = PinkNoiseGenerator()
        self.drift_x = 0.0
        self.drift_y = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.string_sway = 0.0
        self.string_noise = PinkNoiseGenerator()
        self.leg_phase = 0.0
        # Pendulum physics (swing when pushed by mouse wind)
        self.swing_angle = 0.0  # radians from vertical
        self.swing_vel = 0.0

    def update(self, mouse_pos=None):
        # Slow horizontal drift + gentle 1/f vertical bob
        nx = self.noise_x.next()
        ny = self.noise_y.next()
        target_y = self.base_y + ny * 6
        self.vel_y += (target_y - self.y) * 0.001
        self.vel_y *= 0.995
        self.vel_x += nx * 0.006
        self.vel_x *= 0.997
        # Mouse repulsion → push balloon away
        if mouse_pos:
            mx, my = mouse_pos
            dx = self.x - mx
            dy = self.y - my
            dist = max(10, math.sqrt(dx * dx + dy * dy))
            if dist < 150:
                force = (150 - dist) / 150 * 0.15
                self.vel_x += (dx / dist) * force
                self.vel_y += (dy / dist) * force * 0.3
        # Pendulum: gentle 1/f sway + mouse push
        accel_x = self.vel_x - getattr(self, '_prev_vx', self.vel_x)
        self._prev_vx = self.vel_x
        if abs(accel_x) > 0.02:
            self.swing_vel += accel_x * 0.5
        # Only swing from mouse push (no constant sway)
        self.swing_vel -= math.sin(self.swing_angle) * 0.012
        self.swing_vel *= 0.98
        self.swing_angle += self.swing_vel
        self.swing_angle = max(-0.5, min(0.5, self.swing_angle))
        self.x += self.vel_x
        self.y += self.vel_y
        self.y = max(40, self.y)
        # String sway
        sn = self.string_noise.next()
        self.string_sway += (sn * 0.5 - self.string_sway) * 0.02
        # Leg dangle
        self.leg_phase += 0.03

    def draw(self, painter, tint=None, ps=None):
        ps = ps or PIXEL_SIZE
        px = int(self.x)
        py = int(self.y)

        # Balloon (NOT rotated — stays upright)
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush, QRadialGradient
        string_len = 12 * ps
        balloon_y = py - string_len
        balloon_r = ps * 3.5
        bcx = px + 0.5 * ps + self.string_sway * ps * 0.3
        bcy = balloon_y - 4 * ps
        painter.setRenderHint(QPainter.Antialiasing, True)
        grad = QRadialGradient(bcx - balloon_r * 0.3, bcy - balloon_r * 0.3, balloon_r * 1.2)
        hc = QColor(*BALLOON_COLORS['highlight'])
        bc = QColor(*BALLOON_COLORS['balloon'])
        if tint:
            hc = apply_tint(hc, tint)
            bc = apply_tint(bc, tint)
        grad.setColorAt(0.0, hc)
        grad.setColorAt(1.0, bc)
        path = QPainterPath()
        path.addEllipse(bcx - balloon_r, bcy - balloon_r, balloon_r * 2, balloon_r * 2)
        painter.fillPath(path, QBrush(grad))
        kc = QColor(*BALLOON_COLORS['knot'])
        if tint:
            kc = apply_tint(kc, tint)
        painter.fillRect(int(bcx - 1), int(bcy + balloon_r), 3, 3, kc)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Rotate string + body around balloon bottom
        pivot_x = bcx
        pivot_y = bcy + balloon_r
        painter.save()
        painter.translate(pivot_x, pivot_y)
        painter.rotate(math.degrees(self.swing_angle))
        painter.translate(-pivot_x, -pivot_y)

        # String from balloon to Pooh (rotated with body)
        sc = QColor(50, 50, 50, 180)
        for i in range(0, string_len, max(1, ps // 2)):
            t = i / max(1, string_len)
            sx = int(pivot_x + self.string_sway * t * ps * 2)
            sy = int(pivot_y + i)
            painter.fillRect(sx, sy, 1, max(1, ps // 2), sc)

        # Pooh body (smooth QPainterPath — Classic Pooh / E.H. Shepard style)
        painter.setRenderHint(QPainter.Antialiasing, True)

        fur = QColor(210, 175, 75)
        fur_dark = QColor(185, 150, 55)
        fur_light = QColor(225, 195, 100)
        nose_c = QColor(50, 40, 30)
        eye_c = QColor(25, 25, 25)
        if tint:
            fur = apply_tint(fur, tint)
            fur_dark = apply_tint(fur_dark, tint)
            fur_light = apply_tint(fur_light, tint)

        u = ps  # unit size
        cx = px + u * 0.5
        cy = py

        leg_swing = 0

        # Both arms reaching up (side view — one visible arm)
        arm_path = QPainterPath()
        arm_path.moveTo(cx - u * 0.3, cy - u * 4.5)
        arm_path.lineTo(cx - u * 0.5, cy - u * 8.5)
        arm_path.lineTo(cx + u * 0.5, cy - u * 8.5)
        arm_path.lineTo(cx + u * 0.3, cy - u * 4.5)
        arm_path.closeSubpath()
        painter.fillPath(arm_path, QBrush(fur_dark))

        # Body (round tummy)
        body_r_x = u * 2.2
        body_r_y = u * 2.8
        body_cy = cy - u * 2
        body_path = QPainterPath()
        body_path.addEllipse(cx - body_r_x, body_cy - body_r_y, body_r_x * 2, body_r_y * 2)
        body_grad = QRadialGradient(cx - u * 0.5, body_cy - u * 0.5, body_r_x * 1.3)
        body_grad.setColorAt(0.0, fur_light)
        body_grad.setColorAt(1.0, fur)
        painter.fillPath(body_path, QBrush(body_grad))

        # Legs (chubby, side view)
        lx = cx
        ly = cy + u * 0.3
        # Thigh (round, plump)
        thigh = QPainterPath()
        thigh.addEllipse(lx - u * 0.5, ly, u * 2.5, u * 2.0)
        painter.fillPath(thigh, QBrush(fur))
        # Lower leg (extending forward)
        shin = QPainterPath()
        shin.addEllipse(lx + u * 1.0, ly + u * 1.0, u * 2.0, u * 1.5)
        painter.fillPath(shin, QBrush(fur))
        # Foot (round, chubby)
        foot_path = QPainterPath()
        foot_path.addEllipse(lx + u * 2.2, ly + u * 1.5, u * 1.5, u * 1.0)
        painter.fillPath(foot_path, QBrush(fur_dark))

        # Head
        head_r = u * 2.0
        head_cy = cy - u * 5.5
        head_path = QPainterPath()
        head_path.addEllipse(cx - head_r, head_cy - head_r, head_r * 2, head_r * 2)
        head_grad = QRadialGradient(cx - u * 0.5, head_cy - u * 0.5, head_r * 1.2)
        head_grad.setColorAt(0.0, fur_light)
        head_grad.setColorAt(1.0, fur)
        painter.fillPath(head_path, QBrush(head_grad))

        # Ear (side view — one visible on top)
        ear_path = QPainterPath()
        ear_path.addEllipse(cx - u * 0.3, head_cy - head_r - u * 0.2, u * 1.1, u * 1.1)
        painter.fillPath(ear_path, QBrush(fur_dark))

        # Snout / muzzle (side view — protruding forward)
        snout_path = QPainterPath()
        snout_path.addEllipse(cx + u * 0.5, head_cy + u * 0.2, u * 1.8, u * 1.2)
        painter.fillPath(snout_path, QBrush(fur_light))

        # Eye (side view — one visible)
        painter.setBrush(QBrush(eye_c))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx + u * 0.5), int(head_cy - u * 0.3), int(u * 0.5), int(u * 0.5))

        # Nose (on the snout tip)
        painter.setBrush(QBrush(nose_c))
        painter.drawEllipse(int(cx + u * 1.8), int(head_cy + u * 0.5), int(u * 0.5), int(u * 0.4))

        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.restore()  # undo pendulum rotation


# --- Drifting balloon (floats away, shrinks into distance) ---
BALLOON_PALETTE = [
    (220, 60, 60),    # red
    (60, 150, 220),   # blue
    (250, 210, 50),   # yellow
    (100, 200, 100),  # green
    (220, 130, 200),  # pink
    (240, 160, 50),   # orange
    (160, 100, 220),  # purple
]

class DriftBalloon:
    def __init__(self, x, y, rng, area_height, direction=None, radius_min=8, radius_max=14):
        self.x = float(x)
        self.y = float(y)
        self.area_height = area_height
        self.radius_min = radius_min
        self.radius_max = radius_max
        color = rng.choice(BALLOON_PALETTE)
        self.color = QColor(*color)
        self.highlight = QColor(min(255, color[0] + 70), min(255, color[1] + 70), min(255, color[2] + 70))
        self.base_radius = rng.uniform(self.radius_min, self.radius_max)
        self.radius = self.base_radius
        self.shrink_speed = rng.uniform(0.003, 0.008)
        self.noise_x = PinkNoiseGenerator()
        self.noise_y = PinkNoiseGenerator()
        # Speed proportional to size (big = near = fast, small = far = slow)
        d = direction or rng.choice([-1, 1])
        self.speed_scale = self.base_radius / 14.0
        self.vx = d * rng.uniform(0.02, 0.06) * (1 + self.speed_scale)
        self.vy = -rng.uniform(0.15, 0.35)  # rising from below
        self.alive = True

    def update(self, mouse_pos=None):
        nx = self.noise_x.next()
        ny = self.noise_y.next()
        self.vx += nx * 0.0005
        self.vy += ny * 0.0003
        # Mouse repulsion + shrink (blown into distance)
        if mouse_pos:
            mx, my = mouse_pos
            dx = self.x - mx
            dy = self.y - my
            dist = max(5, math.sqrt(dx * dx + dy * dy))
            if dist < 120:
                force = (120 - dist) / 120 * 0.2
                self.vx += (dx / dist) * force
                self.vy += (dy / dist) * force * 0.3
                self.shrink_speed += 0.002  # pushed away = shrinks faster
        self.vx *= 0.998
        self.vy *= 0.998
        self.x += self.vx
        self.y += self.vy
        # Keep within screen (don't fly above visible area)
        self.y = max(self.radius + 2, self.y)
        # Shrink and fade (drifting into distance)
        self.radius -= self.shrink_speed
        if self.radius < 1.0:
            self.alive = False

    def draw(self, painter, tint=None):
        if not self.alive:
            return
        from PyQt5.QtGui import QPainterPath, QPainter, QBrush, QRadialGradient
        r = self.radius
        alpha = max(30, int(255 * (r / self.base_radius)))
        painter.setRenderHint(QPainter.Antialiasing, True)
        grad = QRadialGradient(self.x - r * 0.3, self.y - r * 0.3, r * 1.2)
        hc = apply_tint(QColor(self.highlight), tint) if tint else QColor(self.highlight)
        hc.setAlpha(alpha)
        bc = apply_tint(QColor(self.color), tint) if tint else QColor(self.color)
        bc.setAlpha(alpha)
        grad.setColorAt(0.0, hc)
        grad.setColorAt(1.0, bc)
        path = QPainterPath()
        path.addEllipse(self.x - r, self.y - r, r * 2, r * 2)
        painter.fillPath(path, QBrush(grad))
        # String (trails behind balloon movement — physics correct)
        sc = QColor(50, 50, 50, int(alpha * 0.5))
        string_len = max(2, int(r * 0.8))
        # String direction: opposite of velocity (dragged behind)
        trail_x = -self.vx * 5  # horizontal trail
        trail_y_offset = abs(self.vx) * 2  # less vertical when moving fast
        for i in range(string_len):
            t = i / max(1, string_len)
            sx = self.x + trail_x * t * t  # quadratic → more at tip
            sy = self.y + r + i * max(0.3, 1.0 - abs(self.vx) * 0.5) - trail_y_offset * t
            painter.fillRect(int(sx), int(sy), 1, 1, sc)
        painter.setRenderHint(QPainter.Antialiasing, False)


# --- Cloud ---
class Cloud:
    def __init__(self, x, y, width, speed, rng):
        self.x = float(x)
        self.y = y
        self.width = width
        self.height = max(2, width // 3)
        self.speed = speed
        self.noise = PinkNoiseGenerator()
        self.speed_offset = 0.0
        # Pre-build cloud shape (rounded blob)
        self.pixels = []
        for dx in range(-width, width + 1):
            ratio = 1.0 - (dx / width) ** 2
            h = max(0, int(self.height * math.sqrt(max(0, ratio))))
            for dy in range(h):
                self.pixels.append((dx, dy))

    def update(self, screen_width):
        n = self.noise.next()
        self.speed_offset += (n * 0.1 - self.speed_offset) * 0.01
        self.x += self.speed + self.speed_offset
        if self.x - self.width * PIXEL_SIZE > screen_width:
            self.x = -self.width * PIXEL_SIZE

    def draw(self, painter, ps=None):
        ps = ps or PIXEL_SIZE
        c = QColor(255, 255, 255, 50)
        c_bright = QColor(255, 255, 255, 70)
        for dx, dy in self.pixels:
            draw_x = int(self.x + dx * ps)
            draw_y = int(self.y - dy * ps)
            painter.fillRect(draw_x, draw_y, ps, ps, c_bright if dy > self.height * 0.5 else c)


# --- PoohScene ---
class PoohScene(BaseScene):

    def __init__(self):
        self.pooh = None
        self.tigger = None
        self.eeyore = None
        self.piglet = None
        self.rabbit = None
        self.owl = None
        self.balloons = []
        self.clouds = []
        self.birds = []
        self.widget_width = 0
        self.area_height = 200
        self.scale = 1.0
        self.ps = PIXEL_SIZE

    def get_area_height(self, config):
        s = config.get("pooh_scale", 100) / 100.0
        return int(200 * s)

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("pooh_scale", 100) / 100.0
        self.ps = max(1, int(PIXEL_SIZE * self.scale))
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed)

        # Character visibility
        self._show = {
            'pooh': config.get("pooh_show_pooh", True),
            'tigger': config.get("pooh_show_tigger", True),
            'eeyore': config.get("pooh_show_eeyore", True),
            'piglet': config.get("pooh_show_piglet", True),
            'rabbit': config.get("pooh_show_rabbit", True),
            'owl': config.get("pooh_show_owl", True),
        }

        # Drifting balloons
        self.balloon_count = config.get("pooh_balloon_count", 8)
        self.balloon_size = config.get("pooh_balloon_size", 30)  # 10-100 → maps to radius
        self._b_rmin = max(3, self.balloon_size * 0.2)
        self._b_rmax = max(5, self.balloon_size * 0.7)
        # 左下のハンバーガーボタンのエリアを避ける
        self._avoid = min(hamburger_avoid_px(self.scale), widget_width)
        self.balloons = []
        for i in range(self.balloon_count):
            bx = rng.randint(self._avoid, widget_width)
            by = self.area_height + rng.uniform(0, 50) + i * 15
            self.balloons.append(DriftBalloon(bx, by, rng, self.area_height,
                                              radius_min=self._b_rmin, radius_max=self._b_rmax))

        self.clouds = []

        # Forest on the ground
        self._generate_forest(rng, widget_width)

        # Pooh floating above
        pooh_x = widget_width * rng.uniform(0.3, 0.7)
        pooh_y = self.area_height * 0.55
        self.pooh = FloatingPooh(pooh_x, pooh_y)

        # Bees
        num_birds = config.get("pooh_bird_count", 3)
        self.birds = []
        for _ in range(num_birds):
            bx = rng.randint(0, widget_width)
            by = rng.uniform(self.area_height * 0.1, self.area_height * 0.5)
            self.birds.append(Bird(bx, by, rng))

        # Friends
        self.tigger = Tigger(0, self.area_height, rng)
        self.tigger.screen_width = widget_width
        self.eeyore = Eeyore(widget_width * rng.uniform(0.15, 0.85),
                             self.area_height * rng.uniform(0.4, 0.6), rng)
        self.piglet = SmallBalloonChar(widget_width * rng.uniform(0.2, 0.8),
                                       self.area_height * rng.uniform(0.3, 0.5), 'piglet', rng)
        self.rabbit = SmallBalloonChar(widget_width * rng.uniform(0.2, 0.8),
                                       self.area_height * rng.uniform(0.35, 0.55), 'rabbit', rng)
        self.owl = Owl(rng.randint(0, widget_width),
                       self.area_height * rng.uniform(0.15, 0.35), rng)

    def _generate_forest(self, rng, width):
        self.forest_elements = []
        x = self._avoid + rng.randint(10, 40)
        while x < width:
            kind = rng.choice(['tree', 'tree', 'tree', 'house', 'bridge'])
            if kind == 'tree':
                pixels = rng.choice(MINI_TREE_VARIANTS)
                self.forest_elements.append((x, pixels, 'tree'))
            elif kind == 'house':
                self.forest_elements.append((x, MINI_HOUSE, 'house'))
            elif kind == 'bridge':
                self.forest_elements.append((x, MINI_BRIDGE, 'bridge'))
            x += rng.randint(30, 80)

    def update(self, wind_sim, mouse_pos=None):
        # Screen wrap for characters
        margin = 80
        for char in [self.pooh, self.eeyore, self.piglet, self.rabbit]:
            if char:
                if char.x > self.widget_width + margin:
                    char.x = -margin
                elif char.x < -margin:
                    char.x = self.widget_width + margin

        # Balloons: update with mouse repulsion and respawn
        for b in self.balloons:
            b.update(mouse_pos)
        self.balloons = [b for b in self.balloons if b.alive]
        while len(self.balloons) < self.balloon_count:
            bx = self.widget_width * random.uniform(0.1, 0.9)
            by = self.area_height + random.uniform(5, 30)
            self.balloons.append(DriftBalloon(bx, by, random.Random(), self.area_height,
                                              radius_min=self._b_rmin, radius_max=self._b_rmax))
        for cloud in self.clouds:
            cloud.update(self.widget_width)
        if self.pooh:
            self.pooh.update(mouse_pos)
        if self.tigger:
            self.tigger.update()
            if self.tigger.x > self.widget_width + 50:
                self.tigger.x = -50
            elif self.tigger.x < -50:
                self.tigger.x = self.widget_width + 50
        if self.eeyore:
            self.eeyore.update(mouse_pos)
        if self.piglet:
            self.piglet.update(mouse_pos)
        if self.rabbit:
            self.rabbit.update(mouse_pos)
        if self.owl:
            self.owl.update()
            if self.owl.x > self.widget_width + 50:
                self.owl.x = -50
            elif self.owl.x < -50:
                self.owl.x = self.widget_width + 50
        for bird in self.birds:
            bird.update()
            # Wrap at edges
            if bird.x > self.widget_width + 30:
                bird.x = -30
            elif bird.x < -30:
                bird.x = self.widget_width + 30
            bird.y = max(0, min(self.area_height * 0.6, bird.y))

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        ps = self.ps

        # Sky gradient
        sky = QLinearGradient(0, 0, 0, ground_y)
        sky.setColorAt(0.0, QColor(135, 190, 235, 0))
        sky.setColorAt(0.5, QColor(155, 205, 240, 15))
        sky.setColorAt(1.0, QColor(175, 215, 230, 25))
        painter.fillRect(0, 0, self.widget_width, ground_y, sky)

        # Drifting balloons (behind characters)
        for b in self.balloons:
            b.draw(painter, tint)

        # Clouds
        for cloud in self.clouds:
            cloud.draw(painter, ps)

        # Birds
        for bird in self.birds:
            bird.draw(painter, ps)

        # Characters (visibility controlled by config)
        if self.eeyore and self._show.get('eeyore', True):
            self.eeyore.draw(painter, tint, ps)
        if self.piglet and self._show.get('piglet', True):
            self.piglet.draw(painter, tint, ps)
        if self.rabbit and self._show.get('rabbit', True):
            self.rabbit.draw(painter, tint, ps)
        if self.owl and self._show.get('owl', True):
            self.owl.draw(painter, tint, ps)
        if self.tigger and self._show.get('tigger', True):
            self.tigger.draw(painter, ground_y, tint, ps)
        if self.pooh and self._show.get('pooh', True):
            self.pooh.draw(painter, tint, ps)


# ---------------------------------------------------------------------------
# プラグイン登録（設定タブ・gather・i18n は main.py から移設）
# ---------------------------------------------------------------------------

def _build_settings(dialog):
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QGroupBox, QLabel, QCheckBox,
    )
    from i18n import t

    tab_pooh = QWidget()
    pooh_layout = QVBoxLayout(tab_pooh)
    dialog.pooh_scale_slider = dialog._add_slider(pooh_layout, t("display_scale"), 25, 200, dialog.config.get("pooh_scale", 100))
    # Character ON/OFF
    char_group = QGroupBox(t("pooh_characters"))
    char_layout = QVBoxLayout(char_group)
    dialog.pooh_pooh_check = QCheckBox("Winnie-the-Pooh")
    dialog.pooh_pooh_check.setChecked(dialog.config.get("pooh_show_pooh", True))
    dialog.pooh_pooh_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_pooh_check)
    dialog.pooh_tigger_check = QCheckBox("Tigger")
    dialog.pooh_tigger_check.setChecked(dialog.config.get("pooh_show_tigger", True))
    dialog.pooh_tigger_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_tigger_check)
    dialog.pooh_eeyore_check = QCheckBox("Eeyore")
    dialog.pooh_eeyore_check.setChecked(dialog.config.get("pooh_show_eeyore", True))
    dialog.pooh_eeyore_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_eeyore_check)
    dialog.pooh_piglet_check = QCheckBox("Piglet")
    dialog.pooh_piglet_check.setChecked(dialog.config.get("pooh_show_piglet", True))
    dialog.pooh_piglet_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_piglet_check)
    dialog.pooh_rabbit_check = QCheckBox("Rabbit")
    dialog.pooh_rabbit_check.setChecked(dialog.config.get("pooh_show_rabbit", True))
    dialog.pooh_rabbit_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_rabbit_check)
    dialog.pooh_owl_check = QCheckBox("Owl")
    dialog.pooh_owl_check.setChecked(dialog.config.get("pooh_show_owl", True))
    dialog.pooh_owl_check.toggled.connect(dialog._on_slider_changed)
    char_layout.addWidget(dialog.pooh_owl_check)
    pooh_layout.addWidget(char_group)

    dialog.pooh_balloon_slider = dialog._add_slider(pooh_layout, t("pooh_balloon_count"), 0, 400, dialog.config.get("pooh_balloon_count", 8))
    dialog.pooh_balloon_size_slider = dialog._add_slider(pooh_layout, t("pooh_balloon_size"), 1, 30, dialog.config.get("pooh_balloon_size", 30))
    dialog.pooh_bird_slider = dialog._add_slider(pooh_layout, t("pooh_bird_count"), 0, 10, dialog.config.get("pooh_bird_count", 3))

    # Credit notice
    credit = QLabel(t("pooh_credit"))
    credit.setWordWrap(True)
    credit.setStyleSheet("color: #888; font-size: 9px; margin-top: 8px;")
    pooh_layout.addWidget(credit)
    pooh_layout.addStretch()

    return [(tab_pooh, t("pooh_settings"))]


def _gather(dialog):
    return {
        "pooh_scale": dialog.pooh_scale_slider.value(),
        "pooh_show_pooh": dialog.pooh_pooh_check.isChecked(),
        "pooh_show_tigger": dialog.pooh_tigger_check.isChecked(),
        "pooh_show_eeyore": dialog.pooh_eeyore_check.isChecked(),
        "pooh_show_piglet": dialog.pooh_piglet_check.isChecked(),
        "pooh_show_rabbit": dialog.pooh_rabbit_check.isChecked(),
        "pooh_show_owl": dialog.pooh_owl_check.isChecked(),
        "pooh_balloon_count": dialog.pooh_balloon_slider.value(),
        "pooh_balloon_size": dialog.pooh_balloon_size_slider.value(),
        "pooh_bird_count": dialog.pooh_bird_slider.value(),
    }


SCENE = {
    "key": "pooh",
    "label_key": "scene_pooh",
    "class": PoohScene,
    "order": 40,
    "scale_key": "pooh_scale",
    "preset_keys": ["pooh_scale", "pooh_balloon_count", "pooh_balloon_size", "pooh_bird_count", "seed"],
    "texts": {
        "ja": {
            "scene_pooh": "風船プーさん",
            "pooh_settings": "プーさん設定",
            "pooh_credit": "出典：A・A・ミルネ著／E・H・シェパード挿絵\n『クマのプーさん』（1926年）、『プー横丁にたった家』（1928年）\n※原著（パブリックドメイン）をベースに制作",
            "pooh_characters": "キャラクター表示",
            "pooh_balloon_count": "飛ぶ風船の数",
            "pooh_balloon_size": "風船サイズ",
            "pooh_cloud_count": "雲の数",
            "pooh_bird_count": "鳥の数",
        },
        "en": {
            "scene_pooh": "Balloon Pooh",
            "pooh_settings": "Pooh Settings",
            "pooh_credit": "Based on \"Winnie-the-Pooh\" (1926) and \"The House at Pooh Corner\" (1928)\nby A.A. Milne, illustrated by E.H. Shepard. (Public Domain)",
            "pooh_characters": "Characters",
            "pooh_balloon_count": "Flying Balloons",
            "pooh_balloon_size": "Balloon Size",
            "pooh_cloud_count": "Clouds",
            "pooh_bird_count": "Birds",
        },
    },
    "build_settings": _build_settings,
    "gather": _gather,
}
