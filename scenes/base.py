"""Base scene class and shared utilities"""
import random
from PyQt5.QtGui import QColor

PIXEL_SIZE = 4

# 画面左下のハンバーガーメニューボタンの基準サイズ（表示倍率1.0のときのpx）
HAMBURGER_BASE = 48


def hamburger_avoid_px(scale):
    """左下のハンバーガーボタン用に空けておくエリアの幅(px)"""
    return int((HAMBURGER_BASE + 16) * scale)


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


def apply_tint(color, tint):
    """QColor に tint (r,g,b) の掛け算を適用して新しい QColor を返す"""
    if tint is None:
        return QColor(color)
    r, g, b = tint
    return QColor(
        min(255, int(color.red() * r)),
        min(255, int(color.green() * g)),
        min(255, int(color.blue() * b)),
    )


# 雨の天気状態（weather_fx の state 名と同期）
RAINY_STATES = frozenset({
    "drizzle", "rain", "heavy_rain", "rain_showers",
    "freezing_rain", "thunderstorm",
})


class BaseScene:
    """All scenes implement these methods"""

    weather_state = "clear"

    def set_weather(self, state):
        """現在の天気を伝える（毎tick、ScreenOverlayから）"""
        self.weather_state = state or "clear"

    @property
    def is_raining(self):
        return self.weather_state in RAINY_STATES

    def get_area_height(self, config):
        """Return overlay area height in screen pixels"""
        raise NotImplementedError

    def rebuild(self, config, screen_width, widget_width):
        """Generate / regenerate scene elements"""
        raise NotImplementedError

    def update(self, wind_sim, mouse_pos=None):
        """Per-frame animation update"""
        raise NotImplementedError

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        """Draw the scene.
        get_alpha(screen_x) -> int(0..255), or None for full opacity.
        """
        raise NotImplementedError

    def has_background_layer(self):
        """Whether this scene has a separate background layer (behind other windows)"""
        return False

    def draw_background(self, painter, ground_y, tint=None, get_alpha=None):
        """Draw background elements (rendered behind other windows)"""
        pass
