"""
天気エフェクト — 3レイヤー奥行き付きの雨・雪描画
奥: 小さく遅い / 中: 中間 / 手前: 大きく速い
"""
import random
import math
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt

# =============================================
# 雨量別の基本パラメータ（中間レイヤー基準）
# =============================================
RAIN_PARAMS = {
    "drizzle":       {"count": 12,  "speed": 5, "bounce": 0.6, "color": (140, 180, 220)},
    "rain":          {"count": 30,  "speed": 7, "bounce": 0.8, "color": (120, 160, 210)},
    "heavy_rain":    {"count": 60,  "speed": 10, "bounce": 0.9, "color": (100, 140, 200)},
    "rain_showers":  {"count": 40,  "speed": 8, "bounce": 0.85, "color": (110, 150, 205)},
    "freezing_rain": {"count": 20,  "speed": 6, "bounce": 0.7, "color": (160, 200, 230)},
    "thunderstorm":  {"count": 80,  "speed": 14, "bounce": 0.95, "color": (80, 120, 180)},
}

SNOW_PARAMS = {
    "snow":          {"count": 15,  "speed": 1.2, "color": (230, 240, 255)},
    "heavy_snow":    {"count": 35,  "speed": 1.5, "color": (220, 235, 255)},
    "snow_showers":  {"count": 25,  "speed": 1.3, "color": (225, 238, 255)},
}

# 3レイヤー定義: (速度倍率, サイズ倍率, アルファ, 粒数倍率)
RAIN_LAYERS = [
    {"speed_mult": 0.5, "size_mult": 0.5, "alpha": 20,  "count_mult": 0.6},  # 奥
    {"speed_mult": 1.0, "size_mult": 1.0, "alpha": 40,  "count_mult": 1.0},  # 中
    {"speed_mult": 1.5, "size_mult": 1.5, "alpha": 65,  "count_mult": 0.5},  # 手前
]

SNOW_LAYERS = [
    {"speed_mult": 0.5, "size_mult": 0.5, "alpha": 30,  "count_mult": 0.6},  # 奥
    {"speed_mult": 1.0, "size_mult": 1.0, "alpha": 55,  "count_mult": 1.0},  # 中
    {"speed_mult": 1.5, "size_mult": 1.5, "alpha": 85,  "count_mult": 0.5},  # 手前
]

NO_EFFECT_STATES = {"clear", "mainly_clear", "partly_cloudy", "overcast", "fog", "unknown"}

# 風速定数
WIND_SPEED_CALM = 15
WIND_SPEED_MAX = 60


class RainDrop:
    """雨粒（レイヤー付き）"""
    def __init__(self, x, screen_width, ground_y, speed, size, alpha, color, bounce_chance):
        self.x = x
        self.y = random.uniform(0, ground_y)
        self.screen_width = screen_width
        self.ground_y = ground_y
        self.base_speed = speed + random.uniform(-1, 1)
        self.speed = self.base_speed
        self.size = max(2, int(size))
        self.alpha = alpha
        self.color = QColor(*color, alpha)
        self.bounce_chance = bounce_chance
        self.drift = random.uniform(-0.3, 0.3)
        # 跳ね返り
        self.bouncing = False
        self.bounce_frame = 0
        self.bounce_x = 0
        self.bounce_particles = []

    def update(self, wind_drift=0):
        if self.bouncing:
            self.bounce_frame += 1
            if self.bounce_frame > 12:
                self._reset()
            return

        self.y += self.speed
        self.x += self.drift + wind_drift * (self.size / 6)

        if self.y >= self.ground_y:
            if random.random() < self.bounce_chance:
                self.bouncing = True
                self.bounce_frame = 0
                self.bounce_x = self.x
                self.bounce_particles = []
                for _ in range(random.randint(4, 8)):
                    self.bounce_particles.append({
                        "dx": random.uniform(-7, 7),
                        "dy": random.uniform(-8, -2),
                        "size": random.randint(1, max(2, self.size // 2)),
                    })
            else:
                self._reset()

    def _reset(self):
        self.bouncing = False
        self.bounce_frame = 0
        self.y = random.uniform(-30, 0)
        self.x = random.randint(0, self.screen_width)

    def draw(self, painter):
        if self.bouncing:
            self._draw_bounce(painter)
        else:
            self._draw_drop(painter)

    def _draw_drop(self, painter):
        """雨粒: 傾きのある線"""
        x, y = int(self.x), int(self.y)
        s = self.size
        slant = int(self.drift * 3)
        for i in range(s * 2):
            px = x + int(slant * i / max(1, s * 2))
            py = y + i
            painter.fillRect(px, py, max(1, s // 2), 1, self.color)

    def _draw_bounce(self, painter):
        progress = self.bounce_frame / 12.0
        alpha = int(self.alpha * (1 - progress))
        c = QColor(self.color)
        c.setAlpha(max(0, alpha))
        for p in self.bounce_particles:
            px = int(self.bounce_x + p["dx"] * self.bounce_frame * 0.8)
            py = int(self.ground_y + p["dy"] * self.bounce_frame * 0.7 + 0.3 * self.bounce_frame ** 2)
            painter.fillRect(px, py, p["size"], p["size"], c)


class SnowFlake:
    """雪片: 丸いひらひら（レイヤー付き）"""
    def __init__(self, x, screen_width, ground_y, speed, size, alpha, color):
        self.x = x
        self.y = random.uniform(0, ground_y)
        self.screen_width = screen_width
        self.ground_y = ground_y
        self.speed = speed + random.uniform(-0.3, 0.3)
        self.size = max(2, int(size))
        self.alpha = alpha
        self.color = QColor(*color, alpha)
        # ひらひら揺れ
        self.phase = random.uniform(0, math.pi * 2)
        self.sway_speed = random.uniform(0.03, 0.08)
        self.sway_amount = random.uniform(1.0, 3.0)
        # 着地フェード
        self.landed = False
        self.fade_frame = 0

    def update(self, wind_drift=0):
        if self.landed:
            self.fade_frame += 1
            if self.fade_frame > 10:
                self._reset()
            return

        self.phase += self.sway_speed
        sway = math.sin(self.phase) * self.sway_amount
        self.y += self.speed
        self.x += sway + wind_drift * 0.5

        if self.y >= self.ground_y:
            self.landed = True
            self.fade_frame = 0

    def _reset(self):
        self.landed = False
        self.fade_frame = 0
        self.y = random.uniform(-30, 0)
        self.x = random.randint(0, self.screen_width)
        self.phase = random.uniform(0, math.pi * 2)

    def draw(self, painter):
        x, y = int(self.x), int(self.y)
        s = self.size

        if self.landed:
            # 地面でフェードアウト
            progress = self.fade_frame / 10.0
            alpha = int(self.alpha * (1 - progress))
            c = QColor(self.color)
            c.setAlpha(max(0, alpha))
            self._draw_circle(painter, x, int(self.ground_y - s), s, c)
        else:
            self._draw_circle(painter, x, y, s, self.color)

    def _draw_circle(self, painter, cx, cy, r, color):
        """ドット絵風の丸"""
        if r <= 2:
            painter.fillRect(cx, cy, r, r, color)
            return
        # 簡易円: 中央が太く上下が細い
        for dy in range(-r // 2, r // 2 + 1):
            half_w = int(math.sqrt(max(0, (r / 2) ** 2 - dy ** 2)))
            if half_w > 0:
                painter.fillRect(cx - half_w, cy + dy, half_w * 2, 1, color)


class Lightning:
    """雷: 画面全体の閃光＋フラクタル（midpoint displacement）で生成した
    本物らしく折れ曲がり分岐する稲妻。雷雨(thunderstorm)のときだけ 1/f 的に光る。
    稲妻は上端でフェードイン（始点の線が見えない）し、しばらく残ってから消える。"""
    BOLT_LIFE = 24   # 稲妻の残存フレーム（約90fpsで0.27秒）

    def __init__(self):
        self.flash = 0.0          # 画面フラッシュの強さ 0..1
        self.bolt = None          # {"main":[(x,y)...], "branches":[[...],...]}
        self.bolt_frame = 0
        self._timer = random.uniform(1.5, 5.0)  # 次の落雷までの秒数

    def update(self, dt, screen_width, ground_y):
        if self.flash > 0:
            self.flash *= 0.88     # 閃光の減衰（稲妻が残る間ほのかに照らす）
            if self.flash < 0.02:
                self.flash = 0.0
        if self.bolt is not None:
            self.bolt_frame += 1
            if self.bolt_frame > self.BOLT_LIFE:
                self.bolt = None
        self._timer -= dt
        if self._timer <= 0:
            self._strike(screen_width, ground_y)
            # 次までの間隔（たまに連続、たいていは間が空く）
            self._timer = random.choice(
                [random.uniform(0.1, 0.5), random.uniform(2.5, 7.0),
                 random.uniform(2.5, 7.0)])

    def _fractal(self, x0, y0, x1, y1, disp, depth):
        """midpoint displacement で2点間を自然なギザギザに分割"""
        if depth <= 0:
            return [(x0, y0), (x1, y1)]
        mx = (x0 + x1) / 2 + random.uniform(-disp, disp)
        my = (y0 + y1) / 2 + random.uniform(-disp * 0.25, disp * 0.25)
        left = self._fractal(x0, y0, mx, my, disp * 0.55, depth - 1)
        right = self._fractal(mx, my, x1, y1, disp * 0.55, depth - 1)
        return left[:-1] + right

    def _strike(self, w, ground_y):
        self.flash = random.uniform(0.55, 1.0)
        if random.random() < 0.6:   # 稲妻ボルト（残りは閃光のみ）
            x = random.uniform(w * 0.2, w * 0.8)
            end_x = x + random.uniform(-w * 0.12, w * 0.12)
            main = self._fractal(x, 0, end_x, ground_y * 0.98,
                                 max(8, w * 0.05), 5)
            branches = []
            # 本物のように途中から枝分かれ（短く・下方向へ）
            for i in range(2, len(main) - 1):
                if random.random() < 0.16:
                    bx, by = main[i]
                    ex = bx + random.uniform(-w * 0.12, w * 0.12)
                    ey = by + random.uniform(ground_y * 0.15, ground_y * 0.4)
                    branches.append(self._fractal(
                        bx, by, ex, min(ey, ground_y), max(5, w * 0.03), 3))
            self.bolt = {"main": main, "branches": branches}
            self.bolt_frame = 0
        else:
            self.bolt = None

    def draw(self, painter, ground_y):
        if self.flash > 0:
            a = int(120 * self.flash)
            painter.fillRect(painter.window(), QColor(220, 230, 255, a))
        if not self.bolt:
            return
        life = max(0.0, 1.0 - self.bolt_frame / float(self.BOLT_LIFE))
        # 最初の数フレームは最も明るく、その後ゆっくり消える
        intensity = life ** 0.6
        fade_zone = max(1.0, ground_y * 0.28)   # 上端フェードの帯

        def seg_alpha(y):
            top = min(1.0, max(0.0, y) / fade_zone)  # 上端ほど透明
            return intensity * top

        self._draw_poly(painter, self.bolt["main"], seg_alpha, 2, 6, 1.0)
        for br in self.bolt["branches"]:
            self._draw_poly(painter, br, seg_alpha, 1, 3, 0.55)

    def _draw_poly(self, painter, pts, seg_alpha, core_w, glow_w, amul):
        if len(pts) < 2:
            return
        for width, base, k in ((glow_w, (150, 180, 255), 0.4),
                               (core_w, (245, 250, 255), 1.0)):
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                a = seg_alpha((y1 + y2) / 2) * amul * k
                col = QColor(base[0], base[1], base[2],
                            max(0, min(255, int(255 * a))))
                pen = painter.pen()
                pen.setColor(col)
                pen.setWidth(width)
                painter.setPen(pen)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.setPen(Qt.NoPen)


class WeatherEffect:
    """天気エフェクトマネージャー（3レイヤー奥行き）"""
    def __init__(self):
        self.drops = []       # RainDrop or SnowFlake のリスト
        self.current_state = "clear"
        self.screen_width = 800
        self.ground_y = 60
        self.wind_speed = 0
        self.lightning = Lightning()

    def set_geometry(self, screen_width, ground_y):
        self.screen_width = screen_width
        self.ground_y = ground_y

    def set_wind_speed(self, speed_kmh):
        self.wind_speed = speed_kmh or 0

    def set_weather(self, weather_state):
        if weather_state == self.current_state:
            return
        self.current_state = weather_state
        self.drops = []

        if weather_state in NO_EFFECT_STATES:
            return

        is_snow = weather_state in SNOW_PARAMS
        params = SNOW_PARAMS.get(weather_state) if is_snow else RAIN_PARAMS.get(weather_state)
        if not params:
            return

        base_count = params["count"]
        base_speed = params["speed"]
        color = params["color"]
        bounce = params.get("bounce", 0)

        layers = SNOW_LAYERS if is_snow else RAIN_LAYERS
        for layer in layers:
            count = max(1, int(base_count * layer["count_mult"]))
            speed = base_speed * layer["speed_mult"]
            size = 5 * layer["size_mult"]  # 基本サイズ5px
            alpha = layer["alpha"]

            for _ in range(count):
                x = random.randint(0, self.screen_width)
                if is_snow:
                    self.drops.append(SnowFlake(
                        x, self.screen_width, self.ground_y,
                        speed, size, alpha, color
                    ))
                else:
                    self.drops.append(RainDrop(
                        x, self.screen_width, self.ground_y,
                        speed, size, alpha, color, bounce
                    ))

    def update(self):
        wind_drift = 0
        if self.wind_speed > WIND_SPEED_CALM:
            ratio = min(1.0, (self.wind_speed - WIND_SPEED_CALM) / (WIND_SPEED_MAX - WIND_SPEED_CALM))
            wind_drift = ratio * 3.0

        for drop in self.drops:
            drop.update(wind_drift)

        # 雷雨のときだけ稲妻（約90fps想定で dt≈1/90）
        if self.current_state == "thunderstorm":
            self.lightning.update(1 / 90.0, self.screen_width, self.ground_y)
        elif self.lightning.flash or self.lightning.bolt:
            self.lightning.flash = 0.0
            self.lightning.bolt = None

    def draw(self, painter):
        for drop in self.drops:
            drop.draw(painter)
        if self.current_state == "thunderstorm":
            self.lightning.draw(painter, self.ground_y)
