# -*- coding: utf-8 -*-
"""1/f モードプラグインの雛形 — 「風に揺れるチューリップ」

このファイルが配布パッケージそのものです（1ファイル = 1モード）。
コピーして好きな名前（例: tulip.py）に変え、プラグインフォルダに置くと
次回起動時にモード一覧へ追加されます。

  プラグインフォルダ:
    Windows: %APPDATA%/1f/plugins/
    mac:     ~/Library/Application Support/1f/plugins/

  検証:   python tools/validate_plugin.py plugins/tulip.py
  ガイド: docs/plugin_guide.md（契約と使えるAPIの全リファレンス）

ファイル名が "_" で始まるもの（この雛形など）は読み込まれません。
"""
import random

from PyQt5.QtGui import QColor

from scenes.base import BaseScene, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from i18n import t

# チューリップの花の色（お好みで追加・変更OK）
FLOWER_COLORS = [
    (231, 76, 90),    # 赤
    (243, 156, 18),   # オレンジ
    (240, 98, 146),   # ピンク
    (255, 222, 89),   # 黄
    (155, 89, 182),   # 紫
]
STEM_COLOR = (76, 145, 65)    # 茎
LEAF_COLOR = (96, 170, 80)    # 葉


class Tulip:
    """1本のチューリップ。base_x は画面上のX座標（揺れの位相に使う）"""

    def __init__(self, base_x, height, color, rng):
        self.base_x = base_x
        self.height = height          # 茎の長さ（ドット数）
        self.color = color
        self.phase = rng.uniform(0, 1)  # 個体差（揺れの効き方）
        self.sway = 0.0

    def update(self, wave):
        # wave は風シミュレータの値（-2..+2 程度）。先端ほど大きく曲がる
        self.sway = wave * (0.8 + self.phase * 0.4)

    def draw(self, painter, ground_y, alpha, tint, ps):
        # 茎: 下から上へ、上にいくほど風で横にずれる
        for i in range(self.height):
            k = i / self.height                     # 0=根元, 1=先端
            dx = int(self.sway * k * k * 3 * ps)    # 先端ほど曲がる
            x = self.base_x + dx
            y = ground_y - (i + 1) * ps
            c = apply_tint(QColor(*STEM_COLOR), tint)
            c.setAlpha(alpha)
            painter.fillRect(x, y, ps, ps, c)
        # 葉: 茎の中ほどに左右1枚ずつ
        mid = self.height // 2
        dx_mid = int(self.sway * 0.25 * 3 * ps)
        leaf = apply_tint(QColor(*LEAF_COLOR), tint)
        leaf.setAlpha(alpha)
        ly = ground_y - mid * ps
        painter.fillRect(self.base_x + dx_mid - ps, ly, ps, ps, leaf)
        painter.fillRect(self.base_x + dx_mid + ps, ly + ps, ps, ps, leaf)
        # 花: 先端に 3x3 ドットのチューリップ型
        tip_dx = int(self.sway * 3 * ps)
        fx = self.base_x + tip_dx - ps
        fy = ground_y - (self.height + 3) * ps
        c = apply_tint(QColor(*self.color), tint)
        c.setAlpha(alpha)
        for col in range(3):
            painter.fillRect(fx + col * ps, fy + ps, ps, ps, c)      # 中段
            painter.fillRect(fx + col * ps, fy + 2 * ps, ps, ps, c)  # 下段
        painter.fillRect(fx, fy, ps, ps, c)             # 上段は左右だけ
        painter.fillRect(fx + 2 * ps, fy, ps, ps, c)    # （V字の切れ込み）


class TulipScene(BaseScene):
    """モード本体。BaseScene の4メソッドを実装すれば動く"""

    def get_area_height(self, config):
        """タスクバー上に確保する高さ(px)。表示倍率に連動させる"""
        scale = config.get("tulip_scale", 100) / 100.0
        return int(130 * scale)

    def rebuild(self, config, screen_width, widget_width):
        """設定変更・再生成のたびに呼ばれる。seed で再現可能にすること"""
        self.scale = config.get("tulip_scale", 100) / 100.0
        self.pixel_size = max(1, int(PIXEL_SIZE * self.scale))
        rng = random.Random(config.get("seed", 0))
        count = config.get("tulip_count", 12)
        # 画面左下のメニューボタンのエリアは避ける（お約束）
        x0 = hamburger_avoid_px(self.scale)
        self.tulips = []
        for _ in range(count):
            x = rng.randint(x0, max(x0 + 1, widget_width - 8))
            h = rng.randint(8, 16)
            color = rng.choice(FLOWER_COLORS)
            self.tulips.append(Tulip(x, h, color, rng))

    def update(self, wind_sim, mouse_pos=None):
        """毎フレーム呼ばれる。wind_sim.get_wave_at(x) が1/fゆらぎの風"""
        for tu in self.tulips:
            tu.update(wind_sim.get_wave_at(tu.base_x))

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        """tint=時間帯ライティング、get_alpha=マウス近接フェード。
        どちらも全ドットに適用するのがお約束"""
        ps = self.pixel_size
        for tu in self.tulips:
            alpha = get_alpha(tu.base_x) if get_alpha else 255
            if alpha <= 0:
                continue
            tu.draw(painter, ground_y, alpha, tint, ps)


def _build_settings(dialog):
    """設定画面のタブを作る。dialog._add_slider が部品を作ってくれる。
    値が変わると自動で gather → 再構築される"""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout
    tab = QWidget()
    layout = QVBoxLayout(tab)
    dialog.tulip_scale_slider = dialog._add_slider(
        layout, t("display_scale"), 25, 200,
        dialog.config.get("tulip_scale", 100))
    dialog.tulip_count_slider = dialog._add_slider(
        layout, t("tulip_count"), 1, 50,
        dialog.config.get("tulip_count", 12))
    layout.addStretch()
    return [(tab, t("tulip_settings"))]


def _gather(dialog):
    """設定タブの現在値を config 辞書で返す（キー名は他モードと被らないこと）"""
    return {
        "tulip_scale": dialog.tulip_scale_slider.value(),
        "tulip_count": dialog.tulip_count_slider.value(),
    }


# ここがプラグインの「契約」。エンジンはこの辞書だけを見る
SCENE = {
    "key": "tulip",                  # モードの内部名（全モードで一意・英小文字）
    "label_key": "scene_tulip",      # モード一覧に出す名前の i18n キー
    "class": TulipScene,             # BaseScene のサブクラス
    "order": 200,                    # 一覧の表示順（ユーザープラグインは 200+ 推奨）
    "scale_key": "tulip_scale",      # 表示倍率の config キー（メニューボタン連動）
    "preset_keys": ["tulip_scale", "tulip_count", "seed"],  # プリセット保存対象
    "texts": {                       # このモード専用のラベル（日英）
        "ja": {
            "scene_tulip": "チューリップ",
            "tulip_settings": "チューリップ設定",
            "tulip_count": "本数",
        },
        "en": {
            "scene_tulip": "Tulips",
            "tulip_settings": "Tulip Settings",
            "tulip_count": "Count",
        },
    },
    # 任意のメタ情報（将来のストア掲載用。今は表示されません）
    "meta": {
        "author": "your-name",
        "version": "1.0.0",
        "description": "風に揺れるピクセルアートのチューリップ",
        "license": "MIT",
    },
    "build_settings": _build_settings,
    "gather": _gather,
}
