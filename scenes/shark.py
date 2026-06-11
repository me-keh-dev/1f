"""Shark scene - cute pixel sharks cruising in the deep sea

深海をゆったり回遊するサメたちのシーン。すべてオリジナルのドット絵。
- サメ: 丸みのあるかわいいシルエット。水の物理（慣性・抵抗）と
  1/fゆらぎで上下にたゆたいながら回遊する。奥行きで縮小＋青く霞む（空気遠近法の水中版）
- 珊瑚: 枝分かれをランダムウォークで生成。手前は彩色、奥は青いシルエット
- 海藻: バネ＋抵抗の水中物理でゆらめく緑の帯
- 光: 水面から差し込む光の柱がゆっくり明滅
- 泡: サメの鼻先や海藻から時々立ちのぼる
"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtGui import QColor, QLinearGradient


# --- サメのドット絵（ぬいぐるみ風・原画は左向き32×16、パース時に反転） ---
# o=輪郭(濃紺), B=体(やわらかい青), W=おなか(白), e=目, s=口のステッチ
SHARK_ART = [
    "............ooo.................",
    "...........oBBBo................",
    "..........oBBBBBo...............",
    ".........oBBBBBBBo.........oo...",
    "....ooooooBBBBBBBooooo....oBBo..",
    "..ooBBBBBBBBBBBBBBBBBBoo.oBBo...",
    ".oBBBBBBBBBBBBBBBBBBBBBooBBo....",
    "oBBBeBBBBBBBBBBBBBBBBBBBBBo.....",
    "oBBBBBBBBBBBBBBBBBBBBBBBBBo.....",
    "osssWWWWWWWWWWWWWWWWBBBBoBBo....",
    ".oWWWWWWWWWWWWWWWWWWBBBoooBBo...",
    "..ooWWWWWWWWWWWWWWWooo....oBBo..",
    "....oooBBBBBooooooo........oo...",
    ".......oBBBo....................",
    "........oBBo....................",
    ".........oo.....................",
]
SHARK_ANCHOR = (12, 8)  # (col, row) が回遊の中心
TAIL_COL = 24           # この列から右（原画）が尾ビレ＝揺れに連動


def _parse_art(art, anchor):
    ax, ay = anchor
    pixels = []
    parts = {"B": "body", "W": "belly", "o": "outline",
             "e": "eye", "s": "mouth"}
    for r, row in enumerate(art):
        for c, ch in enumerate(row):
            if ch in parts:
                part = parts[ch]
                if c >= TAIL_COL:
                    part = "outline_tail" if part == "outline" else "tail"
                # 左向きの原画を反転し、direction=1 で右向きになる座標系に
                pixels.append((ax - c, r - ay, part))
    return pixels


SHARK_SHAPE = _parse_art(SHARK_ART, SHARK_ANCHOR)

# サメの色（ぬいぐるみトーンの青＋濃紺の輪郭、3バリエーション）
SHARK_VARIANTS = [
    {"body": (127, 168, 201), "tail": (127, 168, 201),
     "belly": (244, 247, 249), "eye": (27, 42, 58),
     "mouth": (143, 166, 184), "outline": (46, 74, 102)},
    {"body": (117, 157, 194), "tail": (117, 157, 194),
     "belly": (240, 244, 247), "eye": (27, 42, 58),
     "mouth": (134, 156, 176), "outline": (42, 68, 96)},
    {"body": (139, 177, 208), "tail": (139, 177, 208),
     "belly": (246, 249, 251), "eye": (27, 42, 58),
     "mouth": (152, 174, 190), "outline": (52, 80, 108)},
]

# 奥行きの霞（深海の青）
HAZE_COLOR = (52, 96, 138)

# 珊瑚のパレット（手前用の彩色）
CORAL_COLORS = [
    (212, 124, 134),   # ピンク
    (224, 152, 110),   # オレンジ
    (188, 110, 140),   # 赤紫
    (196, 168, 178),   # 淡いピンク
    (110, 168, 158),   # ティール
]
CORAL_BACK = (40, 78, 112)      # 奥のシルエット
SEAWEED_COLORS = [
    {"dark": (38, 110, 80), "bright": (70, 168, 110)},
    {"dark": (44, 122, 96), "bright": (84, 182, 130)},
]
SAND_COLOR = (58, 92, 120)
SAND_DARK = (44, 74, 100)
RAY_COLOR = (190, 225, 245)


def _haze(color, depth, ratio=0.5):
    """奥行きに応じて深海の青へ溶かす"""
    k = depth * ratio
    return (
        int(color[0] * (1 - k) + HAZE_COLOR[0] * k),
        int(color[1] * (1 - k) + HAZE_COLOR[1] * k),
        int(color[2] * (1 - k) + HAZE_COLOR[2] * k),
    )


# --- サメ ---
class Shark:
    def __init__(self, rng, x, y, depth, min_y, max_y, speed):
        self.x = float(x)
        self.y = float(y)
        self.depth = depth                  # 0=手前 1=奥
        self.min_y = min_y
        self.max_y = max_y
        self.speed = speed * (1.0 - depth * 0.4)
        variant = rng.choice(SHARK_VARIANTS)
        self.colors = {k: QColor(*_haze(v, depth, 0.55))
                       for k, v in variant.items()}
        self.colors["outline_tail"] = self.colors["outline"]
        self.direction = rng.choice([-1, 1])
        self.target_dir = self.direction
        self.vx = self.speed * self.direction
        self.vy = 0.0
        self.swim_phase = rng.uniform(0, math.tau)
        self.noise_y = PinkNoiseGenerator()
        self.think = rng.randint(200, 700)
        self.vy_force = 0.0
        self.alpha_k = 1.0 - depth * 0.35   # 奥は薄く

    def update(self, width):
        self.swim_phase += 0.035 + abs(self.vx) * 0.05
        self.think -= 1
        if self.think <= 0:
            self.think = random.randint(300, 900)
            if random.random() < 0.18:
                self.target_dir *= -1     # たまにゆっくり旋回
            self.vy_force = random.uniform(-0.004, 0.004)
        # 重い体: ゆるい推進と強い慣性
        target_vx = self.speed * self.target_dir
        self.vx += (target_vx - self.vx) * 0.006
        self.vx *= 0.995
        self.vy += self.vy_force + self.noise_y.next() * 0.002
        self.vy *= 0.97
        if self.vx > 0.02:
            self.direction = 1
        elif self.vx < -0.02:
            self.direction = -1
        self.x += self.vx
        self.y += self.vy
        if self.y < self.min_y:
            self.y = self.min_y
            self.vy = abs(self.vy) * 0.3
            self.vy_force = abs(self.vy_force)
        elif self.y > self.max_y:
            self.y = self.max_y
            self.vy = -abs(self.vy) * 0.3
            self.vy_force = -abs(self.vy_force)
        margin = 140
        if self.x > width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = width + margin

    def draw(self, painter, alpha, tint, ps):
        ps = max(1, int(ps * (1.0 - self.depth * 0.45)))
        a = int(alpha * self.alpha_k)
        tail_sway = math.sin(self.swim_phase) * 1.2
        for dx, dy, part in SHARK_SHAPE:
            ddx = dx * self.direction
            ddy = dy
            if part in ("tail", "outline_tail"):
                # 尾ビレは付け根から先端ほど大きく揺れる（輪郭線も一緒に）
                k = min(1.0, max(0, abs(dx) - 12) / 4.0)
                ddx += tail_sway * k * self.direction * (-1)
            elif part in ("body", "belly"):
                ddy += math.sin(self.swim_phase + dx * 0.25) * 0.10
            c = apply_tint(self.colors[part], tint)
            c.setAlpha(a)
            painter.fillRect(int(self.x + ddx * ps), int(self.y + ddy * ps),
                             ps, ps, c)


# --- 珊瑚（枝分かれランダムウォーク） ---
def _gen_coral(rng, height):
    pixels = []

    def branch(x, y, drift, length):
        for i in range(length):
            if rng.random() < 0.65:
                x += drift
            y += 1
            pixels.append((round(x), y))
            pixels.append((round(x) + rng.choice([0, 0, -1, 1]), y))
            if y > 1 and rng.random() < 0.30 and length - i > 2:
                branch(x, y, -drift if rng.random() < 0.7 else drift,
                       (length - i) * 2 // 3)

    n_trunk = rng.randint(2, 3)
    for ti in range(n_trunk):
        bx = (ti - n_trunk // 2) * 2
        pixels.append((bx, 0))
        branch(bx, 0, rng.choice([-1, 1]), rng.randint(max(2, height - 2), height))
    return pixels


class Coral:
    def __init__(self, rng, base_x, height, depth):
        self.base_x = base_x
        self.depth = depth          # 0=手前(彩色) 1=奥(シルエット)
        self.pixels = _gen_coral(rng, height)
        if depth > 0.5:
            col = _haze(CORAL_BACK, depth, 0.5)
            self.alpha_k = 0.55
        else:
            col = _haze(rng.choice(CORAL_COLORS), depth, 0.8)
            self.alpha_k = 0.85
        self.color = QColor(*col)

    def draw(self, painter, ground_y, alpha, tint, ps):
        ps = max(1, int(ps * (1.0 - self.depth * 0.35)))
        c = apply_tint(self.color, tint)
        c.setAlpha(int(alpha * self.alpha_k))
        for dx, dy in self.pixels:
            painter.fillRect(int(self.base_x + dx * ps),
                             int(ground_y - (dy + 1) * ps), ps, ps, c)


# --- 海藻（水中物理でゆらめく帯） ---
class Seaweed:
    def __init__(self, rng, base_x, height, depth):
        self.base_x = base_x
        self.depth = depth
        self.height = height
        pal = rng.choice(SEAWEED_COLORS)
        self.dark = QColor(*_haze(pal["dark"], depth, 0.6))
        self.bright = QColor(*_haze(pal["bright"], depth, 0.6))
        self.noise = PinkNoiseGenerator()
        self.sway = 0.0
        self.sway_vel = 0.0
        self.sway_base = rng.uniform(2.0, 4.5)
        self.phase = rng.uniform(0, math.tau)

    def update(self, wind_wave):
        target = (wind_wave * 0.4 + self.noise.next() * 0.3) * self.sway_base
        self.sway_vel += (target - self.sway) * 0.006
        self.sway_vel *= 0.93
        self.sway += self.sway_vel

    def draw(self, painter, ground_y, alpha, tint, ps):
        ps = max(1, int(ps * (1.0 - self.depth * 0.35)))
        a = int(alpha * (0.9 - self.depth * 0.3))
        for dy in range(self.height):
            sf = dy / max(1, self.height)
            # 帯が波打つ: 揺れ＋固有のうねり
            dx = self.sway * sf + math.sin(sf * 3.0 + self.phase) * 0.8 * sf
            c = self.bright if sf > 0.5 else self.dark
            c = apply_tint(c, tint)
            c.setAlpha(a)
            # 2ピクセル幅の帯（上に行くほど1本に）
            w = 2 * ps if sf < 0.6 else ps
            painter.fillRect(int(self.base_x + dx * ps),
                             int(ground_y - (dy + 1) * ps), w, ps, c)


# --- 泡 ---
class Bubble:
    def __init__(self, x, y, ps):
        self.x = float(x)
        self.y = float(y)
        self.vy = -random.uniform(0.25, 0.6)
        self.vx = 0.0
        self.size = random.choice([1, 1, 2]) * max(2, ps // 2)
        self.alpha = random.randint(90, 160)
        self.alive = True

    def update(self):
        self.vx += random.uniform(-0.02, 0.02)
        self.vx *= 0.95
        self.x += self.vx
        self.y += self.vy
        self.alpha -= 1
        if self.alpha <= 0:
            self.alive = False

    def draw(self, painter):
        if self.alive:
            painter.fillRect(int(self.x), int(self.y), self.size, self.size,
                             QColor(190, 226, 250, self.alpha))


# --- SharkScene ---
class SharkScene(BaseScene):
    def __init__(self):
        self.sharks = []
        self.corals = []
        self.seaweeds = []
        self.bubbles = []
        self.rays = []           # (x_ratio, width_ratio, phase)
        self.bubble_timer = 0
        self.width = 0
        self.area_h = 200
        self.scale = 1.0
        self.ps = PIXEL_SIZE
        self.rays_on = True
        self.bubbles_on = True
        self.t = 0

    def get_area_height(self, config):
        s = config.get("shark_scale", 100) / 100.0
        return max(120, int(210 * s))

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("shark_scale", 100) / 100.0
        self.ps = max(2, int(PIXEL_SIZE * self.scale))
        self.area_h = self.get_area_height(config)
        self.width = widget_width
        self.rays_on = config.get("shark_rays", True)
        self.bubbles_on = config.get("shark_bubbles", True)
        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed ^ 0x5AAC)
        avoid = min(hamburger_avoid_px(self.scale), widget_width)

        # 珊瑚: 量に応じて床に群生（奥のシルエット層＋手前の彩色層）
        coral_amount = config.get("shark_coral", 60)
        self.corals = []
        n_coral = int(widget_width / 90 * coral_amount / 50.0)
        for _ in range(n_coral):
            x = rng.randint(avoid, max(avoid + 1, widget_width - 10))
            depth = rng.choice([0.15, 0.3, 0.7, 0.85])
            h = rng.randint(6, 14)
            self.corals.append(Coral(rng, x, h, depth))

        # 海藻
        weed_amount = config.get("shark_seaweed", 50)
        self.seaweeds = []
        n_weed = int(widget_width / 130 * weed_amount / 50.0)
        for _ in range(n_weed):
            x = rng.randint(avoid, max(avoid + 1, widget_width - 10))
            depth = rng.uniform(0.1, 0.8)
            h = rng.randint(8, 18)
            self.seaweeds.append(Seaweed(rng, x, h, depth))

        # サメ（奥行きを均等に割り当て）
        count = max(1, min(8, config.get("shark_count", 3)))
        self.sharks = []
        min_y = int(self.area_h * 0.18)
        max_y = int(self.area_h * 0.72)
        for i in range(count):
            depth = i / max(1, count - 1) if count > 1 else 0.2
            x = rng.randint(0, widget_width)
            y = rng.randint(min_y, max_y)
            speed = rng.uniform(0.25, 0.45) * self.scale
            self.sharks.append(Shark(rng, x, y, depth, min_y, max_y, speed))

        # 光の柱（水面から差し込む光、ゆっくり明滅）
        self.rays = []
        for k in range(max(2, widget_width // 500)):
            self.rays.append((rng.uniform(0.1, 0.9),
                              rng.uniform(0.03, 0.07),
                              rng.uniform(0, math.tau)))
        self.bubbles = []

    def update(self, wind_sim, mouse_pos=None):
        self.t += 1
        for s in self.sharks:
            s.update(self.width)
        for w in self.seaweeds:
            w.update(wind_sim.get_wave_at(w.base_x))
        if self.bubbles_on:
            self.bubble_timer += 1
            if self.bubble_timer % 30 == 0:
                if self.sharks and random.random() < 0.5:
                    s = random.choice(self.sharks)
                    nose = s.x + 12 * s.direction * self.ps
                    self.bubbles.append(Bubble(nose, s.y - self.ps, self.ps))
                elif self.seaweeds:
                    w = random.choice(self.seaweeds)
                    self.bubbles.append(Bubble(
                        w.base_x, self.area_h - w.height * self.ps, self.ps))
            for b in self.bubbles:
                b.update()
            self.bubbles = [b for b in self.bubbles if b.alive and b.y > -10]
            if len(self.bubbles) > 40:
                self.bubbles = self.bubbles[-40:]

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        ps = self.ps
        # 深海のグラデーション（上は明るい青、下は深い青）
        gradient = QLinearGradient(0, ground_y - self.area_h, 0, ground_y)
        gradient.setColorAt(0.0, QColor(70, 130, 170, 60))
        gradient.setColorAt(0.6, QColor(36, 84, 126, 80))
        gradient.setColorAt(1.0, QColor(20, 56, 92, 110))
        painter.fillRect(0, ground_y - self.area_h, self.width, self.area_h,
                         gradient)

        # 光の柱
        if self.rays_on:
            top_y = ground_y - self.area_h
            for xr, wr, phase in self.rays:
                a = 14 + 10 * math.sin(self.t * 0.006 + phase)
                if a <= 0:
                    continue
                rx = int(self.width * xr + math.sin(self.t * 0.002 + phase) * 30)
                rw = max(8, int(self.width * wr))
                g = QLinearGradient(0, top_y, 0, ground_y)
                c = apply_tint(QColor(*RAY_COLOR), tint)
                c.setAlpha(int(a))
                g.setColorAt(0.0, c)
                c2 = QColor(c)
                c2.setAlpha(0)
                g.setColorAt(0.85, c2)
                painter.fillRect(rx, top_y, rw, self.area_h, g)

        # 砂地
        sand = apply_tint(QColor(*SAND_COLOR), tint)
        sand.setAlpha(150)
        painter.fillRect(0, ground_y - 2 * ps, self.width, 2 * ps, sand)
        srng = random.Random(1234)
        dark = apply_tint(QColor(*SAND_DARK), tint)
        dark.setAlpha(140)
        for _ in range(self.width // 40):
            painter.fillRect(srng.randint(0, max(1, self.width)),
                             ground_y - srng.choice([1, 2]) * ps, ps, ps, dark)

        # 奥の珊瑚・海藻 → 奥のサメ → 手前の珊瑚・海藻 → 手前のサメ
        def a_at(x):
            return get_alpha(int(x)) if get_alpha else 255

        for c in self.corals:
            if c.depth > 0.5:
                c.draw(painter, ground_y, a_at(c.base_x), tint, ps)
        for w in self.seaweeds:
            if w.depth > 0.5:
                w.draw(painter, ground_y, a_at(w.base_x), tint, ps)
        for s in sorted(self.sharks, key=lambda s: -s.depth):
            if s.depth > 0.5:
                s.draw(painter, a_at(s.x), tint, ps)
        for c in self.corals:
            if c.depth <= 0.5:
                c.draw(painter, ground_y, a_at(c.base_x), tint, ps)
        for w in self.seaweeds:
            if w.depth <= 0.5:
                w.draw(painter, ground_y, a_at(w.base_x), tint, ps)
        for s in sorted(self.sharks, key=lambda s: -s.depth):
            if s.depth <= 0.5:
                s.draw(painter, a_at(s.x), tint, ps)

        # 泡（最前面）
        for b in self.bubbles:
            b.draw(painter)
