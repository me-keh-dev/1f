"""Window scene - City view through horizontal windows with YouTube fixed cameras
Foreground curtains and plants sway with 1/f yuragi wind.
Windows are landscape-oriented (wider than tall), arranged in a grid.
"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint
from PyQt5.QtGui import QColor


# --- Default camera presets (user can customize in settings) ---
DEFAULT_CAMERAS = [
    {"name": "Relaxing City Walk", "url": "https://www.youtube.com/watch?v=SvyBe662y_w"},
    {"name": "Rain on Window", "url": "https://www.youtube.com/watch?v=UwTQu09Alrw"},
    {"name": "City Night Drive", "url": "https://www.youtube.com/watch?v=X4qZVZBYp-4"},
    {"name": "Cafe Ambience", "url": "https://www.youtube.com/watch?v=qXbqBFqgcbM"},
    {"name": "Cozy Fireplace", "url": "https://www.youtube.com/watch?v=6vUgcA9BxEM"},
    {"name": "Tokyo Tower", "url": "https://www.youtube.com/watch?v=GHSuInSkSHI"},
    {"name": "Shibuya Crossing", "url": "https://www.youtube.com/watch?v=Pk9CLicNyIg"},
    {"name": "Night City Aerial", "url": "https://www.youtube.com/watch?v=g2McuwrRJe8"},
]


def youtube_url_to_embed(url):
    """Convert a YouTube URL to embed format. Returns embed URL or original if already embed."""
    if "youtube.com/embed/" in url:
        return url
    video_id = None
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    elif "watch?v=" in url:
        video_id = url.split("watch?v=")[-1].split("&")[0]
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&controls=0&modestbranding=1&rel=0&showinfo=0"
    return url


def _compute_window_grid(width, height, cols=8, rows=2, wall_h=12, wall_w=20, frame=3):
    """Compute grid positions for horizontal windows.

    Returns list of (x, y, w, h) for each window opening.
    Also returns list of wall rects for the HTML mask.
    """
    # Vertical layout: top_wall | row0 | mid_wall | row1 | bottom_wall
    total_wall_h = (rows + 1) * wall_h
    win_h = max(10, (height - total_wall_h) // rows)

    # Horizontal layout: edge_wall | win | wall | win | ... | edge_wall
    total_wall_w = (cols + 1) * wall_w
    win_w = max(20, (width - total_wall_w) // cols)

    windows = []
    for r in range(rows):
        wy = wall_h + r * (win_h + wall_h)
        for c in range(cols):
            wx = wall_w + c * (win_w + wall_w)
            windows.append((wx, wy, win_w, win_h))

    return windows, win_w, win_h


def generate_window_html(video_url, width, height, cols=8, rows=2,
                         wall_thickness=20, frame_width=3,
                         clip_x=50, clip_y=50, clip_zoom=150,
                         use_video_tag=False):
    """Generate HTML for horizontal window grid: video + CSS wall pieces.

    The video fills the entire background as a single image.
    Wall pieces (top/bottom bars + vertical pillars) are layered on top,
    leaving gaps where the windows are. All 3 windows look into the same scene.
    """
    wall_h = wall_thickness
    wall_w = wall_thickness

    windows, win_w, win_h = _compute_window_grid(
        width, height, cols, rows, wall_h, wall_w, frame_width
    )

    # Colors
    wall_base = "#1e1e2e"
    wall_light = "#2a2a3e"
    wall_dark = "#141420"
    frame_color = "#3a3a4e"
    frame_hi = "#4a4a5e"
    frame_lo = "#303040"

    # Build wall pieces: horizontal bars + vertical pillars
    wall_pieces = []

    # Top bar (full width)
    wall_pieces.append((0, 0, width, wall_h))

    # Bottom bar (full width)
    bottom_y = height - wall_h
    if rows > 0:
        last_row_bottom = windows[-1][1] + windows[-1][3]  # y + h of last window
        bottom_y = last_row_bottom
    wall_pieces.append((0, bottom_y, width, height - bottom_y))

    # Horizontal bars between rows
    for r in range(1, rows):
        bar_y = wall_h + r * (win_h + wall_h) - wall_h
        wall_pieces.append((0, bar_y, width, wall_h))

    # Vertical pillars (left edge, between columns, right edge)
    for r in range(rows):
        row_y = wall_h + r * (win_h + wall_h)
        # Left edge pillar
        wall_pieces.append((0, row_y, wall_w, win_h))
        # Pillars between windows
        for c in range(1, cols):
            px = wall_w + c * (win_w + wall_w) - wall_w
            wall_pieces.append((px, row_y, wall_w, win_h))
        # Right edge pillar
        right_x = wall_w + cols * (win_w + wall_w) - wall_w
        wall_pieces.append((right_x, row_y, width - right_x, win_h))

    html = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #0a0a14; }}

/* Wall pieces layered on top of video */
.wall {{
    position: absolute;
    background: linear-gradient(180deg, {wall_light} 0%, {wall_base} 40%, {wall_dark} 100%);
    z-index: 10;
}}
.wall::after {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        180deg,
        transparent 0px, transparent 10px,
        rgba(255,255,255,0.015) 10px, rgba(255,255,255,0.015) 11px
    );
}}

/* Window frame borders (purely decorative, on top of everything) */
.frame {{
    position: absolute;
    z-index: 20;
    border: {frame_width}px solid {frame_color};
    border-top-color: {frame_hi};
    border-bottom-color: {frame_lo};
    pointer-events: none;
}}
.frame::after {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    pointer-events: none;
}}

/* Video background - single scene visible through all windows */
.video-bg {{
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    overflow: hidden;
    z-index: 1;
}}
.video-bg video, .video-bg iframe {{
    position: absolute;
    width: {max(100, clip_zoom)}%;
    height: {max(100, clip_zoom)}%;
    object-fit: cover;
    object-position: {clip_x}% {clip_y}%;
    left: {-(max(100, clip_zoom) - 100) * clip_x / 100}%;
    top: {-(max(100, clip_zoom) - 100) * clip_y / 100}%;
    border: none;
    pointer-events: none;
}}

/* Fallback cityscape (no video / loading) */
.no-video {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(180deg, #080818 0%, #0c0c22 30%, #101030 60%, #0a0a18 100%);
    z-index: 1;
}}
.star {{
    position: absolute;
    width: 2px; height: 2px;
    background: #fff;
    border-radius: 50%;
    animation: twinkle var(--dur) infinite;
    opacity: 0.3;
    z-index: 2;
}}
@keyframes twinkle {{
    0%, 100% {{ opacity: 0.15; }}
    50% {{ opacity: 0.85; }}
}}
.city-light {{
    position: absolute;
    width: 2px; height: 2px;
    background: #ffeebb;
    animation: city-glow var(--dur) infinite;
    opacity: 0.4;
    z-index: 2;
}}
@keyframes city-glow {{
    0%, 100% {{ opacity: 0.2; }}
    30% {{ opacity: 0.9; }}
    70% {{ opacity: 0.4; }}
}}
</style></head><body>
"""

    # Fallback cityscape (always present, video covers it when loaded)
    rng = random.Random(42)
    html += '<div class="no-video">'
    for _ in range(40):
        sx, sy = rng.randint(0, width), rng.randint(0, int(height * 0.45))
        dur, delay = rng.uniform(2, 7), rng.uniform(0, 5)
        html += f'<div class="star" style="left:{sx}px;top:{sy}px;--dur:{dur:.1f}s;animation-delay:{delay:.1f}s;"></div>'
    for _ in range(60):
        lx = rng.randint(0, width)
        ly = rng.randint(int(height * 0.35), int(height * 0.9))
        dur, delay = rng.uniform(1.5, 9), rng.uniform(0, 6)
        color = rng.choice(["#ffeebb", "#ffddaa", "#ffe4cc", "#fff", "#aaddff", "#ffccaa"])
        html += f'<div class="city-light" style="left:{lx}px;top:{ly}px;--dur:{dur:.1f}s;animation-delay:{delay:.1f}s;background:{color};"></div>'
    html += '</div>'

    # Video layer (single video visible through all windows)
    if video_url:
        if use_video_tag:
            html += f"""
<div class="video-bg">
    <video src="{video_url}" autoplay muted loop playsinline></video>
</div>"""
        else:
            html += f"""
<div class="video-bg">
    <iframe src="{video_url}" allow="autoplay; encrypted-media" loading="lazy"></iframe>
</div>"""

    # Wall pieces (opaque, on top of video - gaps between them = windows)
    for (px, py, pw, ph) in wall_pieces:
        html += f'<div class="wall" style="left:{px}px;top:{py}px;width:{pw}px;height:{ph}px;"></div>'

    # Window frames (decorative borders around each opening)
    for (wx, wy, ww, wh) in windows:
        html += f'<div class="frame" style="left:{wx-frame_width}px;top:{wy-frame_width}px;width:{ww+frame_width*2}px;height:{wh+frame_width*2}px;"></div>'

    html += '</body></html>'
    return html


# --- Foreground elements: Curtains and windowsill plants (QPainter, 1/f yuragi) ---

class Curtain:
    """Pixel-art curtain that sways with wind. Hangs from top of a horizontal window."""
    def __init__(self, x, top_y, win_height, side, color_base):
        self.x = x
        self.top_y = top_y
        self.side = side  # 'left' or 'right'
        self.color_base = color_base
        self.noise = PinkNoiseGenerator()
        self.sway = 0.0
        self.sway_vel = 0.0
        # Curtain height: roughly 60-80% of window height
        self.curtain_h = max(3, int(win_height / PIXEL_SIZE * 0.75))
        self.pixels = self._generate_pixels()

    def _generate_pixels(self):
        """Generate curtain shape - gathered at top, flowing down."""
        pixels = []
        for dy in range(self.curtain_h):
            ratio = dy / max(1, self.curtain_h - 1)
            # Width: narrow at top (gathered), wider at bottom
            w = int(1 + ratio * 2.5)
            for dx in range(w):
                if self.side == 'left':
                    pixels.append((dx, dy))
                else:
                    pixels.append((-dx, dy))
        return pixels

    def update(self, wind_wave):
        local = self.noise.next()
        target = (wind_wave * 0.5 + local * 0.3) * 1.2
        force = (target - self.sway) * 0.015
        self.sway_vel += force
        self.sway_vel *= 0.90  # fabric drag
        self.sway += self.sway_vel

    def draw(self, painter, ground_y, alpha=255, tint=None):
        ps = PIXEL_SIZE
        r, g, b = self.color_base
        for dx, dy in self.pixels:
            ratio = dy / max(1, self.curtain_h - 1)
            sway_offset = self.sway * ratio * ratio
            sx = int(self.x + (dx + sway_offset) * ps)
            sy = int(self.top_y + dy * ps)
            shade = 0.75 + 0.25 * (abs(dx) / 4.0)
            c = QColor(int(r * shade), int(g * shade), int(b * shade))
            if tint:
                c = apply_tint(c, tint)
            c.setAlpha(int(alpha * (0.65 + 0.35 * ratio)))
            painter.fillRect(sx, sy, ps, ps, c)


class WindowPlant:
    """Small plant/vine on the windowsill, swaying with wind."""
    def __init__(self, base_x, base_y, height, palette):
        self.base_x = base_x
        self.base_y = base_y
        self.height = height
        self.palette = palette  # (dark, mid, bright)
        self.noise = PinkNoiseGenerator()
        self.sway = 0.0
        self.sway_vel = 0.0
        self.pixels = self._generate_pixels(height)

    def _generate_pixels(self, height):
        """Generate a small vine/plant growing upward."""
        pixels = []
        rng = random.Random()
        cx = 0.0
        curve_dir = rng.choice([-1, 1])
        for dy in range(height):
            ratio = dy / max(1, height - 1)
            cx += curve_dir * 0.3
            if rng.random() < 0.15:
                curve_dir *= -1
            shade = 0 if ratio < 0.3 else (1 if ratio < 0.7 else 2)
            pixels.append((round(cx), dy, shade))
            if dy > 2 and rng.random() < 0.3:
                leaf_dir = rng.choice([-1, 1])
                pixels.append((round(cx) + leaf_dir, dy, 2))
                if rng.random() < 0.5:
                    pixels.append((round(cx) + leaf_dir * 2, dy, 2))
        return pixels

    def update(self, wind_wave):
        local = self.noise.next()
        target = (wind_wave * 0.3 + local * 0.2) * 2.0
        force = (target - self.sway) * 0.01
        self.sway_vel += force
        self.sway_vel *= 0.92
        self.sway += self.sway_vel

    def draw(self, painter, alpha=255, tint=None):
        ps = PIXEL_SIZE
        max_dy = max((p[1] for p in self.pixels), default=1)
        for dx, dy, shade in self.pixels:
            ratio = dy / max(1, max_dy)
            sway_offset = self.sway * ratio
            sx = int(self.base_x + (dx + sway_offset) * ps)
            sy = int(self.base_y - dy * ps)
            c = QColor(*self.palette[shade])
            if tint:
                c = apply_tint(c, tint)
            c.setAlpha(alpha)
            painter.fillRect(sx, sy, ps, ps, c)


# Plant palettes (green vine colors)
PLANT_PALETTES = [
    ((30, 60, 30), (40, 90, 40), (60, 130, 60)),
    ((25, 55, 35), (35, 85, 50), (55, 120, 70)),
    ((30, 50, 25), (45, 80, 35), (65, 115, 50)),
]

# Curtain color options
CURTAIN_COLORS = [
    (200, 195, 180),  # Off-white / linen
    (180, 170, 155),  # Beige
    (160, 150, 140),  # Gray
    (170, 160, 175),  # Lavender gray
    (175, 165, 150),  # Warm gray
]


class WindowScene(BaseScene):
    """Window mode scene - manages foreground elements (curtains, plants).
    The YouTube video background is handled by the WindowOverlay widget.
    Windows are horizontal (landscape) arranged in a grid.
    """
    AREA_HEIGHT = 120

    def __init__(self):
        self.curtains = []
        self.plants = []
        self.window_rects = []  # (x, y, w, h) of each window
        self.widget_width = 0
        self.area_height = self.AREA_HEIGHT
        self.scale = 1.0

    def get_area_height(self, config):
        s = config.get("win_scale", 100) / 100.0
        return int(self.AREA_HEIGHT * s)

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("win_scale", 100) / 100.0
        self.widget_width = widget_width
        self.area_height = self.get_area_height(config)

        cols = config.get("win_columns", 3)
        rows = config.get("win_rows", 1)
        wall_thickness = config.get("win_wall_thickness", 22)

        windows, win_w, win_h = _compute_window_grid(
            widget_width, self.area_height, cols, rows,
            wall_h=wall_thickness, wall_w=wall_thickness
        )
        self.window_rects = windows

        rng = random.Random(config.get("seed", 42))
        self._generate_curtains(rng, config, win_h)
        self._generate_plants(rng, config)

    def _generate_curtains(self, rng, config, win_h):
        self.curtains = []
        if not config.get("win_curtains", True):
            return
        for wx, wy, ww, wh in self.window_rects:
            if rng.random() < 0.6:  # 60% of windows have curtains
                color = rng.choice(CURTAIN_COLORS)
                # Left curtain (inside window, near left edge)
                self.curtains.append(Curtain(wx + 4, wy + 2, wh, 'left', color))
                # Right curtain (inside window, near right edge)
                self.curtains.append(Curtain(wx + ww - 4, wy + 2, wh, 'right', color))

    def _generate_plants(self, rng, config):
        self.plants = []
        if not config.get("win_plants", True):
            return
        for wx, wy, ww, wh in self.window_rects:
            if rng.random() < 0.3:  # 30% of windows have a small plant
                plant_h = rng.randint(3, 7)
                palette = rng.choice(PLANT_PALETTES)
                px = wx + rng.randint(8, max(9, ww - 12))
                py = wy + wh - 2  # Bottom of window
                self.plants.append(WindowPlant(px, py, plant_h, palette))

    def update(self, wind_sim, mouse_pos=None):
        for c in self.curtains:
            wave = wind_sim.get_wave_at(c.x)
            c.update(wave)
        for p in self.plants:
            wave = wind_sim.get_wave_at(p.base_x)
            p.update(wave)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        """Draw foreground elements (curtains + plants) over the web view."""
        for c in self.curtains:
            alpha = get_alpha(c.x) if get_alpha else 255
            c.draw(painter, ground_y, alpha, tint)
        for p in self.plants:
            alpha = get_alpha(p.base_x) if get_alpha else 255
            p.draw(painter, alpha, tint)
