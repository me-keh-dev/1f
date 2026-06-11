"""Skating scene - figure skaters on a frozen lake at night

夜の凍った湖の天然リンク。スケーターは実在のアイスダンス・
パターンダンスの軌跡（リンクを周回する閉回路＋中央線側/フェンス側へ
交互に膨らむローブの連なり）に沿って滑走し、1/fゆらぎのタイミングで
スピン（トラベリング）・ジャンプ・スパイラルを演じる。
奥行きは画面上の上下位置とサイズで表現。
氷にはトレース（軌跡）と姿の反射が残り、雪が舞う。
"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap


# --- 衣装パレット（dress=衣装, trim=スカート縁・飾り） ---
COSTUMES = [
    {"dress": (205, 60, 95),  "trim": (240, 160, 180)},   # クリムゾン
    {"dress": (70, 95, 210),  "trim": (160, 190, 250)},   # ロイヤルブルー
    {"dress": (150, 80, 210), "trim": (210, 170, 245)},   # バイオレット
    {"dress": (45, 165, 155), "trim": (150, 225, 215)},   # ティール
    {"dress": (225, 175, 60), "trim": (250, 225, 150)},   # ゴールド
    {"dress": (235, 235, 245), "trim": (180, 200, 230)},  # ホワイト
]
HAIR_COLORS = [(40, 30, 28), (25, 25, 30), (120, 80, 40), (190, 150, 80), (90, 45, 30)]
SKIN = (240, 205, 175)
TIGHTS = (235, 230, 235)
SKATE = (245, 245, 250)
BLADE = (185, 200, 215)

# --- ポーズ（dx, dy, part）。dyは上向き正、dy=0がブレード接地ライン。
#     dx正が進行方向（右向き基準、左向きはミラー） ---
POSES = {
    # ストローク（押し）: スタンディング姿勢で片脚を斜め後ろへ伸ばし
    # エッジで氷を押す。ブレードは氷に着いたまま
    "stroke_push": [
        # 支持脚（直立、体の下）
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'),
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        # 押し脚（斜め後ろへ、ブレードは氷上）
        (-1, 3, 'tights'), (-2, 2, 'tights'),
        (-3, 1, 'skate'), (-4, 0, 'blade'), (-3, 0, 'blade'),
        # 腰・スカート
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'trim'),
        (0, 6, 'dress'), (1, 6, 'dress'),
        (0, 7, 'dress'), (1, 7, 'dress'),
        # 腕（軽く前後に振る）
        (2, 7, 'skin'), (3, 6, 'skin'),
        (-1, 7, 'skin'), (-2, 7, 'skin'),
        # 頭
        (0, 8, 'skin'), (1, 8, 'skin'), (0, 9, 'skin'), (1, 9, 'skin'),
        (0, 10, 'hair'), (1, 10, 'hair'), (-1, 9, 'hair'),
    ],
    # ストローク（戻し）: 押した脚を体の下へ引き寄せて両足で滑る
    "stroke_glide": [
        # 両足を揃えて滑る
        (0, 0, 'blade'), (1, 0, 'blade'), (2, 0, 'blade'),
        (1, 1, 'skate'), (0, 1, 'skate'),
        (1, 2, 'tights'), (1, 3, 'tights'), (1, 4, 'tights'),
        (0, 2, 'tights'), (0, 3, 'tights'),
        # 腰・スカート
        (0, 5, 'trim'), (1, 5, 'dress'), (2, 5, 'trim'),
        (1, 6, 'dress'), (2, 6, 'dress'),
        (1, 7, 'dress'), (2, 7, 'dress'),
        # 腕（体側へ流す）
        (3, 7, 'skin'), (3, 6, 'skin'),
        (0, 7, 'skin'), (0, 6, 'skin'),
        # 頭
        (1, 8, 'skin'), (2, 8, 'skin'), (1, 9, 'skin'), (2, 9, 'skin'),
        (1, 10, 'hair'), (2, 10, 'hair'), (0, 9, 'hair'),
    ],
    # 後ろ向きストローク（押し）: バックでは蹴る脚が体の前方へ出る
    # （体は進行方向と逆を向いているので「前足が出る」形になる）
    "stroke_push_back": [
        # 支持脚（直立、体の下）
        (0, 0, 'blade'), (1, 0, 'blade'),
        (1, 1, 'skate'),
        (1, 2, 'tights'), (1, 3, 'tights'), (1, 4, 'tights'),
        # 押し脚（体の前方へ、ブレードは氷上）
        (2, 3, 'tights'), (3, 2, 'tights'),
        (4, 1, 'skate'), (5, 0, 'blade'), (4, 0, 'blade'),
        # 腰・スカート
        (0, 5, 'trim'), (1, 5, 'dress'), (2, 5, 'trim'),
        (1, 6, 'dress'), (2, 6, 'dress'),
        (1, 7, 'dress'), (2, 7, 'dress'),
        # 腕（バランスを取って軽く広げる）
        (3, 7, 'skin'), (4, 6, 'skin'),
        (0, 7, 'skin'), (-1, 7, 'skin'),
        # 頭
        (1, 8, 'skin'), (2, 8, 'skin'), (1, 9, 'skin'), (2, 9, 'skin'),
        (1, 10, 'hair'), (2, 10, 'hair'), (0, 9, 'hair'),
    ],
    # アップライトスピン: 直立、両腕を頭上へ
    "spin": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'), (1, 1, 'skate'),
        (0, 2, 'tights'), (1, 2, 'tights'),
        (0, 3, 'tights'), (1, 3, 'tights'),
        (0, 4, 'tights'), (1, 4, 'tights'),
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'dress'), (2, 5, 'trim'),
        (0, 6, 'dress'), (1, 6, 'dress'),
        (0, 7, 'dress'), (1, 7, 'dress'),
        (0, 8, 'skin'), (1, 8, 'skin'), (0, 9, 'skin'), (1, 9, 'skin'),
        (0, 10, 'hair'), (1, 10, 'hair'),
        (0, 11, 'skin'), (1, 11, 'skin'),
        (0, 12, 'skin'), (1, 12, 'skin'),
    ],
    # シットスピン: 深くしゃがみ、フリーレッグを前へ氷と平行に伸ばす
    "spin_sit": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'),
        # 深く曲げた支持脚
        (0, 2, 'tights'), (1, 2, 'tights'),
        # 前へ伸ばすフリーレッグ（氷と平行）
        (2, 2, 'tights'), (3, 2, 'tights'), (4, 2, 'tights'),
        (5, 2, 'skate'), (6, 2, 'blade'),
        # 低い腰・スカート
        (-1, 3, 'trim'), (0, 3, 'dress'), (1, 3, 'trim'),
        (0, 4, 'dress'), (1, 4, 'dress'),
        # 前へ伸ばす腕
        (2, 4, 'skin'), (3, 4, 'skin'), (4, 4, 'skin'),
        # 頭
        (0, 5, 'skin'), (1, 5, 'skin'), (0, 6, 'skin'), (1, 6, 'skin'),
        (0, 7, 'hair'), (1, 7, 'hair'),
    ],
    # キャメルスピン: 上体とフリーレッグを水平に（アラベスク姿勢で回転）
    "spin_camel": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'),
        # 垂直の支持脚
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        # 後方へ水平のフリーレッグ
        (-1, 5, 'tights'), (-2, 5, 'tights'), (-3, 5, 'tights'),
        (-4, 5, 'skate'), (-5, 5, 'blade'),
        # 腰〜前方へ水平の上体
        (0, 5, 'trim'), (1, 5, 'dress'), (2, 5, 'dress'), (3, 5, 'dress'),
        # 腕（左右＝下へ広げる）
        (2, 4, 'skin'), (2, 6, 'skin'),
        # 頭（前方）
        (4, 5, 'skin'), (5, 5, 'skin'), (4, 6, 'skin'), (5, 6, 'skin'),
        (4, 7, 'hair'), (5, 7, 'hair'),
    ],
    # ドーナツスピン: キャメルから膝を曲げ、頭上に回したブレードを
    # 掴んで体で輪（ドーナツ）を作る
    "spin_donut": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'),
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        # 輪の下側: 腰〜水平の上体と頭（前方）
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'dress'), (2, 5, 'dress'),
        (3, 5, 'skin'), (4, 5, 'skin'),
        (3, 6, 'hair'), (4, 6, 'hair'),
        # 輪の後ろ〜上: 曲げたフリーレッグが頭上へ回り込む
        (-2, 6, 'tights'), (-2, 7, 'tights'), (-1, 8, 'tights'),
        (0, 9, 'tights'), (1, 9, 'tights'), (2, 9, 'skate'), (3, 9, 'blade'),
        # 腕: 頭上へ伸ばしてブレードを掴む
        (4, 7, 'skin'), (4, 8, 'skin'), (3, 8, 'skin'),
    ],
    # ビールマンスピン: 直立のまま後ろのフリーレッグを頭上まで
    # 引き上げ、両手でブレードを掴む
    "spin_biellmann": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'),
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'trim'),
        (0, 6, 'dress'), (1, 6, 'dress'),
        (0, 7, 'dress'), (1, 7, 'dress'),
        # 頭
        (0, 8, 'skin'), (1, 8, 'skin'), (0, 9, 'skin'), (1, 9, 'skin'),
        (0, 10, 'hair'), (1, 10, 'hair'),
        # 後ろから頭上へ引き上げたフリーレッグ
        (-1, 6, 'tights'), (-2, 7, 'tights'), (-2, 8, 'tights'),
        (-2, 9, 'tights'), (-1, 10, 'tights'), (-1, 11, 'tights'),
        (0, 12, 'skate'), (1, 12, 'blade'), (2, 12, 'blade'),
        # 両腕を頭上へ（ブレードを掴む）
        (2, 9, 'skin'), (2, 10, 'skin'), (2, 11, 'skin'),
        (0, 11, 'skin'),
    ],
    # ジャンプ: 空中でタックして回転
    "jump": [
        (0, 0, 'blade'), (1, 0, 'blade'),
        (0, 1, 'skate'), (1, 1, 'skate'),
        (0, 2, 'tights'), (1, 2, 'tights'), (2, 2, 'tights'),
        (2, 3, 'tights'),
        (0, 3, 'dress'), (1, 3, 'dress'),
        (0, 4, 'dress'), (1, 4, 'dress'),
        (-1, 4, 'skin'), (2, 4, 'skin'),
        (0, 5, 'dress'), (1, 5, 'dress'),
        (0, 6, 'skin'), (1, 6, 'skin'), (0, 7, 'skin'), (1, 7, 'skin'),
        (0, 8, 'hair'), (1, 8, 'hair'),
    ],
    # バックスケーティング（後ろ向き滑走）: 背面ビュー。
    # 両腕を左右に大きく広げ、片脚をクロスして滑る（バッククロス）
    "back": [
        # 軸足
        (-1, 0, 'blade'), (0, 0, 'blade'),
        (0, 1, 'skate'),
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        # クロスする脚（横へ伸びる）
        (2, 4, 'tights'), (3, 3, 'tights'),
        (4, 2, 'skate'), (4, 1, 'blade'), (5, 1, 'blade'),
        # 腰・スカート
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'dress'), (2, 5, 'trim'),
        # 背中
        (0, 6, 'dress'), (1, 6, 'dress'),
        (0, 7, 'dress'), (1, 7, 'dress'),
        # 大きく広げた両腕
        (-1, 8, 'dress'), (-2, 8, 'dress'), (-3, 8, 'dress'), (-4, 8, 'skin'),
        (2, 8, 'dress'), (3, 8, 'dress'), (4, 8, 'dress'), (5, 8, 'skin'),
        # 頭（背面なので髪のみ）＋ポニーテール
        (0, 8, 'hair'), (1, 8, 'hair'),
        (0, 9, 'hair'), (1, 9, 'hair'),
        (0, 10, 'hair'), (1, 10, 'hair'),
        (2, 9, 'hair'), (2, 8, 'hair'),
    ],
    # 正面ビュー: 手前へ向かって滑ってくる（顔が見える）。
    # 体は back と同じくバッククロス姿勢で腕を広げる
    "front": [
        (-1, 0, 'blade'), (0, 0, 'blade'),
        (0, 1, 'skate'),
        (0, 2, 'tights'), (0, 3, 'tights'), (0, 4, 'tights'),
        (2, 4, 'tights'), (3, 3, 'tights'),
        (4, 2, 'skate'), (4, 1, 'blade'), (5, 1, 'blade'),
        (-1, 5, 'trim'), (0, 5, 'dress'), (1, 5, 'dress'), (2, 5, 'trim'),
        (0, 6, 'dress'), (1, 6, 'dress'),
        (0, 7, 'dress'), (1, 7, 'dress'),
        (-1, 8, 'dress'), (-2, 8, 'dress'), (-3, 8, 'dress'), (-4, 8, 'skin'),
        (2, 8, 'dress'), (3, 8, 'dress'), (4, 8, 'dress'), (5, 8, 'skin'),
        # 頭（正面なので顔が見え、上に髪）
        (0, 8, 'skin'), (1, 8, 'skin'),
        (0, 9, 'skin'), (1, 9, 'skin'),
        (-1, 9, 'hair'), (2, 9, 'hair'),
        (0, 10, 'hair'), (1, 10, 'hair'),
    ],
    # スパイラル: 上体を前へ、フリーレッグを後方高く
    "spiral": [
        (1, 0, 'blade'), (2, 0, 'blade'), (3, 0, 'blade'),
        (2, 1, 'skate'),
        (2, 2, 'tights'), (2, 3, 'tights'), (2, 4, 'tights'),
        # フリーレッグ（後方高く）
        (1, 5, 'trim'), (0, 6, 'tights'), (-1, 7, 'tights'), (-2, 8, 'tights'),
        (-3, 9, 'skate'), (-4, 9, 'blade'),
        # 腰〜前傾上体
        (2, 5, 'dress'), (3, 6, 'dress'), (4, 6, 'dress'),
        # 腕（左右に広げる）
        (5, 7, 'skin'), (6, 7, 'skin'), (3, 7, 'skin'),
        # 頭（前方）
        (5, 8, 'skin'), (6, 8, 'skin'), (5, 9, 'skin'), (6, 9, 'skin'),
        (5, 10, 'hair'), (6, 10, 'hair'),
    ],
}

# スピンの種類（アップライト/シット/キャメル/ドーナツ/ビールマン）
SPIN_POSES = ["spin", "spin_sit", "spin_camel", "spin_donut", "spin_biellmann"]

# 背景・氷の色（夜の凍った湖）。実際のリンクの氷は白に近い
ICE_COLOR = (208, 220, 232)
ICE_EDGE = (240, 248, 255)
BANK_COLOR = (170, 185, 205)
TREE_COLOR = (16, 28, 42)
TREE_SNOW = (175, 192, 215)
TRAIL_COLOR = (120, 145, 172)  # 白い氷の上では跡はやや暗い線に見える
SNOW_COLOR = (235, 242, 250)
STAR_COLOR = (240, 244, 255)

TRAIL_LIFE = 220  # トレースの寿命（フレーム）
TICK_FPS = 90          # OverlayManager のタイマー（11ms ≈ 90fps）
SKATER_HEIGHT_M = 1.65  # スケーターの身長（pxとmの換算基準）
SKATER_HEIGHT_UNITS = 13  # ポーズの高さ（ユニット）
RINK_DEPTH_M = 12.0    # 奥行き方向（z 0..1）が表す実距離

# ジャンプの物理: 実際のスケーターの跳躍高は最大でも0.5m前後。
# 滞空時間は自由落下の式 t = 2*sqrt(2h/g) から導く（約0.6秒）
JUMP_HEIGHT_M = 0.45
JUMP_HEIGHT_UNITS = JUMP_HEIGHT_M * SKATER_HEIGHT_UNITS / SKATER_HEIGHT_M
JUMP_FRAMES = int(2.0 * math.sqrt(2.0 * JUMP_HEIGHT_M / 9.81) * TICK_FPS)

# --- 実在のISUパターンダンス ---
# 軌跡は実際のパターン図（ISU 2006 図 / 2024 JSF アイスダンス・テスト資料）
# から制御点として採取し、閉じたCatmull-Romスプラインで滑らかに辿る。
# 座標はリンク正規化 (u: リンク長手 0..1, v: リンク幅 0=奥 .. 1=手前)。
# 全パターン共通で反時計回りの閉回路。
PATTERN_DANCES = [
    # ダッチワルツ: プログレッシブとスイングロールでリンクを周回する
    # 初級ワルツ。両サイド中央がくびれた緩い砂時計型のパターン
    {"name": "Dutch Waltz", "speed": 0.85, "points": [
        (0.50, 0.72), (0.64, 0.90), (0.82, 0.93), (0.93, 0.78),
        (0.95, 0.50), (0.93, 0.22), (0.82, 0.07), (0.64, 0.10),
        (0.50, 0.28), (0.36, 0.10), (0.18, 0.07), (0.07, 0.22),
        (0.05, 0.50), (0.07, 0.78), (0.18, 0.93), (0.36, 0.90),
    ]},
    # ヨーロピアンワルツ: 両サイドに半円形の深いローブを3つずつ連ね、
    # 両端は丸いカーブで接続する（図のとおり中央線まで深く切れ込む）
    {"name": "European Waltz", "speed": 1.0, "points": [
        (0.10, 0.86), (0.21, 0.56), (0.32, 0.86), (0.43, 0.56),
        (0.54, 0.86), (0.65, 0.56), (0.76, 0.86), (0.88, 0.88),
        (0.95, 0.65), (0.95, 0.35), (0.88, 0.12), (0.76, 0.14),
        (0.65, 0.44), (0.54, 0.14), (0.43, 0.44), (0.32, 0.14),
        (0.21, 0.44), (0.10, 0.14), (0.04, 0.35), (0.04, 0.65),
    ]},
    # キリアン: フェンス沿いを速いマーチで周回する浅いパターン。
    # 片側の中央でチョクトーにより内側へ一段切れ込む
    {"name": "Kilian", "speed": 1.35, "points": [
        (0.10, 0.90), (0.30, 0.93), (0.50, 0.90), (0.70, 0.93),
        (0.88, 0.88), (0.96, 0.65), (0.96, 0.35), (0.88, 0.12),
        (0.70, 0.08), (0.56, 0.16), (0.46, 0.34), (0.36, 0.14),
        (0.20, 0.08), (0.06, 0.16), (0.03, 0.50), (0.06, 0.80),
    ]},
    # フォーティーンステップ: 両端の大きな円形ローブを中央のくびれで
    # つなぐダンベル型のパターン（図のとおり中央で深く絞られる）
    {"name": "Fourteenstep", "speed": 1.25, "points": [
        (0.50, 0.66), (0.60, 0.80), (0.74, 0.92), (0.88, 0.85),
        (0.95, 0.62), (0.95, 0.38), (0.88, 0.15), (0.74, 0.08),
        (0.60, 0.20), (0.50, 0.34), (0.40, 0.20), (0.26, 0.08),
        (0.12, 0.15), (0.05, 0.38), (0.05, 0.62), (0.12, 0.85),
        (0.26, 0.92), (0.40, 0.80),
    ]},
]

# 奥行き表現: z=0(奥)〜1(手前) に対するスケールと、
# 氷面上のブレード位置（氷バンド上端からの割合）
DEPTH_SCALE_FAR = 0.60   # 奥にいるときのサイズ倍率
LANE_FAR = 0.18          # 奥のブレード位置（氷上端からの割合）
LANE_NEAR = 0.85         # 手前のブレード位置


class Skater:
    """実在パターンダンスの周回軌道に沿って滑走するスケーター"""

    def __init__(self, rng, base_ps, dance, s0, min_x, max_x):
        self.rng = rng
        self.base_ps = base_ps
        self.dance = dance         # PATTERN_DANCES の1つ
        self.s = s0                # 周回パラメータ（0..tau で1周）
        # リンクの幾何（パターン図の正規化座標を画面xへ写像する範囲）
        span = max(20.0, max_x - min_x)
        self.min_x = min_x + span * 0.03
        self.max_x = max_x - span * 0.03
        self.x, self.z = self._pattern_pos(self.s)
        self.dir = 1
        self.costume = rng.choice(COSTUMES)
        self.hair = rng.choice(HAIR_COLORS)
        self.noise = PinkNoiseGenerator()        # 体の揺れ用
        self.speed_noise = PinkNoiseGenerator()  # 滑走速度のゆらぎ用
        self.timing_noise = PinkNoiseGenerator()  # 演技の間合いのゆらぎ用
        self.sway = 0.0
        self.speed = rng.uniform(0.85, 1.15)  # 個人差（テンポ倍率）
        self.rot = 0.0    # スピン/ジャンプの回転位相
        self.air = 0.0    # ジャンプの高さ（単位px）
        self.spray = 0    # 着氷時の氷しぶき残りフレーム
        self.trail = []   # [x, lane_px, age] 氷上のトレース
        self.frame = 0
        self.state = "glide"
        self.timer = rng.randint(60, 150)
        self.ps = base_ps
        self.lane = 0
        self.stroke = rng.uniform(0.0, 2.0)  # ストローク位相（0..2で左右1往復）
        self.spin_pose = "spin"  # 現在のスピンの種類
        self.jump_streak = 0     # 連続ジャンプ回数（2連続まで）
        self.queued = None       # ため区間の後に予約された演技
        self.backward = False   # 後ろ向き滑走中か（体の向き＝進行方向の逆）
        self.depth_dom = False  # 奥行き方向の動きが支配的か
        self.away = False       # 奥へ向かって進んでいるか

    def _pattern_pos(self, s):
        """周回パラメータ s (0..tau) から氷上の位置 (x, z) を返す。
        実際のパターン図から採取した制御点を閉じたCatmull-Rom
        スプラインで補間し、図のとおりの軌跡を滑らかに辿る。
        """
        pts = self.dance["points"]
        n = len(pts)
        t = (s % math.tau) / math.tau * n
        i = int(t) % n
        u = t - int(t)
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]

        def cr(a, b, c, d):
            return 0.5 * (2 * b + (-a + c) * u
                          + (2 * a - 5 * b + 4 * c - d) * u * u
                          + (-a + 3 * b - 3 * c + d) * u * u * u)

        ux = cr(p0[0], p1[0], p2[0], p3[0])
        vz = cr(p0[1], p1[1], p2[1], p3[1])
        x = self.min_x + ux * (self.max_x - self.min_x)
        return x, min(1.0, max(0.0, vz))

    def _enter(self, state):
        self.state = state
        # 演技の間合いも1/fゆらぎ（ピンクノイズで持続時間を伸縮）
        k = 1.0 + 0.6 * self.timing_noise.next()
        if state == "glide":
            self.timer = max(40, int(self.rng.randint(70, 170) * k))
            # 後ろ向き滑走（バックスケーティング）の区間もある
            self.backward = self.rng.random() < 0.35
        elif state == "spin":
            self.timer = max(30, int(self.rng.randint(55, 105) * k))
            # スピンの種類をランダムに選ぶ
            self.spin_pose = self.rng.choice(SPIN_POSES)
        elif state == "jump":
            self.timer = JUMP_FRAMES
            self.jump_streak += 1
        else:  # spiral
            self.timer = max(50, int(self.rng.randint(80, 140) * k))
        if state != "jump" and self.queued != "jump":
            self.jump_streak = 0

    def _next_state(self):
        # ため区間の後に予約済みの演技があればそれを実行
        if self.queued:
            q = self.queued
            self.queued = None
            self._enter(q)
            return
        r = self.rng.random()
        if r < 0.40:
            self._enter("glide")
        elif r < 0.62:
            self._enter("spin")
        elif r < 0.84 and self.jump_streak < 2:
            # ジャンプは2連続まで。着地した足でそのまま跳ばず、
            # 少し滑って「ため」を作ってから2本目を跳ぶ
            if self.state == "jump":
                self.queued = "jump"
                self._enter("glide")
                self.timer = self.rng.randint(30, 60)  # 約0.3〜0.7秒のため
            else:
                self._enter("jump")
        else:
            self._enter("spiral")

    def update(self, wind_wave, trail_on, ice_h):
        self.frame += 1
        # 奥行きに応じたサイズとブレード位置
        depth_k = DEPTH_SCALE_FAR + (1.0 - DEPTH_SCALE_FAR) * self.z
        self.ps = max(2, int(round(self.base_ps * depth_k)))
        self.lane = int(ice_h * (1.0 - (LANE_FAR + (LANE_NEAR - LANE_FAR) * self.z)))

        # 1/fゆらぎ: 体の揺れと速度のムラ（それぞれ独立のピンクノイズ）
        self.sway = self.noise.next() * 0.10 + wind_wave * 0.02
        speed_mod = max(0.5, 1.0 + self.speed_noise.next() * 0.20)

        self.timer -= 1
        if self.timer <= 0:
            if self.state == "jump":
                self.spray = 8  # 着氷の氷しぶき
            self._next_state()

        if self.state == "spin":
            self.rot += 0.38
            move = 0.35  # トラベリングスピン（ツイズル風）: 回りながら進む
        elif self.state == "jump":
            self.rot += 0.52
            u = 1.0 - self.timer / JUMP_FRAMES
            # 重力下の放物線（質量によらず軌道は h*4u(1-u)）
            self.air = 4.0 * u * (1.0 - u) * JUMP_HEIGHT_UNITS
            move = 1.0
        else:
            self.rot = 0.0
            self.air = 0.0
            move = 1.0 if self.state == "glide" else 0.6

        # パターンダンスの周回軌道に沿って物理的に妥当な速度で進む。
        # スケーターの描画身長から px/m を換算し、実際のアイスダンス程度の
        # 滑走速度（基準 4 m/s ≈ 14 km/h、ダンスと個人差で約3〜5.5 m/s）で
        # 弧長ベースに移動する（軌道上のどこでも実速度が一定になる）
        ppm = self.base_ps * SKATER_HEIGHT_UNITS / SKATER_HEIGHT_M  # px per meter
        v_mps = 4.0 * self.dance["speed"] * self.speed * speed_mod * move
        eps = 0.002
        ex, ez = self._pattern_pos(self.s + eps)
        dist_m = math.hypot((ex - self.x) / ppm, (ez - self.z) * RINK_DEPTH_M)
        ds = min(0.01, v_mps / TICK_FPS * eps / max(1e-9, dist_m))
        self.s = (self.s + ds) % math.tau
        # ストローク位相: 蹴って→そのまま滑って→蹴って…の繰り返し
        # （0..1で片脚1ストローク。前半の短い区間だけ蹴り、残りは滑走）
        if self.state == "glide":
            self.stroke = (self.stroke + v_mps * 0.28 / TICK_FPS) % 2.0
        old_x, old_z = self.x, self.z
        self.x, self.z = self._pattern_pos(self.s)

        # 体の向き（ミラー）: 前向きなら進行方向、後ろ向き滑走なら逆を向く
        dx = self.x - old_x
        face = -1 if (self.backward and self.state == "glide") else 1
        if dx > 0.15:
            self.dir = face
        elif dx < -0.15:
            self.dir = -face

        # 奥行きの動きが支配的か（実距離px換算で比較）と、その向き
        dz_px = (self.z - old_z) * RINK_DEPTH_M * ppm
        self.depth_dom = abs(dz_px) > abs(dx)
        self.away = dz_px < 0

        if self.spray > 0:
            self.spray -= 1

        # トレース: 氷上を滑っている間だけ刻む
        if trail_on and self.state != "jump" and move > 0.3 and self.frame % 2 == 0:
            self.trail.append([self.x, self.lane, 0])
        for tr in self.trail:
            tr[2] += 1
        if len(self.trail) > TRAIL_LIFE:
            del self.trail[:len(self.trail) - TRAIL_LIFE]
        self.trail = [tr for tr in self.trail if tr[2] < TRAIL_LIFE]

    def _part_color(self, part):
        if part == 'dress':
            return QColor(*self.costume["dress"])
        if part == 'trim':
            return QColor(*self.costume["trim"])
        if part == 'hair':
            return QColor(*self.hair)
        if part == 'skin':
            return QColor(*SKIN)
        if part == 'tights':
            return QColor(*TIGHTS)
        if part == 'skate':
            return QColor(*SKATE)
        return QColor(*BLADE)

    def draw(self, painter, ground_y, tint, alpha):
        ph = self.ps
        base_y = ground_y - self.lane
        body_y = base_y - int(self.air * ph)
        # 奥行きの動きが支配的なときは、体の向きで背面/正面ビューを選ぶ:
        # 奥へ前向き → 背中が見える / 奥へ後ろ向き → 顔が見える
        # 手前へ前向き → 顔が見える / 手前へ後ろ向き → 背中が見える
        mirror = 1
        if self.state == "glide" and self.depth_dom:
            facing_away = self.away != self.backward
            pixels = POSES["back"] if facing_away else POSES["front"]
            # 押す脚を左右交互に（ストローク位相でミラー）
            if self.stroke >= 1.0:
                mirror = -1
        elif self.state == "glide":
            # 蹴り（短）→そのまま滑走（長）の繰り返し。
            # バックでは蹴る脚が後ろではなく体の前方へ出る（前足が出る）
            if (self.stroke % 1.0) < 0.30:
                pixels = POSES["stroke_push_back" if self.backward
                               else "stroke_push"]
            else:
                pixels = POSES["stroke_glide"]
        elif self.state == "spin":
            pixels = POSES[self.spin_pose]
        else:
            pixels = POSES[self.state]
        # スピン/ジャンプは横方向を cos で潰して回転を表現
        if self.state in ("spin", "jump"):
            fscale = math.cos(self.rot)
        else:
            fscale = 1.0
        lean = self.sway + (0.05 * self.dir if self.state == "glide" else 0.0)

        # 氷への反射（上下反転・薄く・ブレードに近い部分のみ）
        ref_alpha_base = int(alpha * 0.20)
        if ref_alpha_base > 0:
            for dx, dy, part in pixels:
                if dy > 6:
                    continue
                ddx = dx * self.dir * mirror * fscale + lean * dy
                px = int(self.x + round(ddx) * ph)
                py = int(base_y + int(self.air * ph) + dy * ph)
                c = apply_tint(self._part_color(part), tint)
                c.setAlpha(int(ref_alpha_base * (1.0 - dy / 8.0)))
                painter.fillRect(px, py, ph, ph, c)

        # 本体
        for dx, dy, part in pixels:
            ddx = dx * self.dir * mirror * fscale + lean * dy
            px = int(self.x + round(ddx) * ph)
            py = int(body_y - (dy + 1) * ph)
            c = apply_tint(self._part_color(part), tint)
            c.setAlpha(alpha)
            painter.fillRect(px, py, ph, ph, c)

        # 着氷の氷しぶき
        if self.spray > 0:
            for _ in range(3):
                ox = self.rng.randint(-3, 3) * max(1, ph // 2)
                oy = self.rng.randint(0, 2) * max(1, ph // 2)
                c = apply_tint(QColor(*SNOW_COLOR), tint)
                c.setAlpha(int(alpha * 0.7 * self.spray / 8.0))
                painter.fillRect(int(self.x + ox), int(base_y - oy),
                                 max(1, ph // 2), max(1, ph // 2), c)

    def draw_trail(self, painter, ground_y, tint, get_alpha):
        ph = max(1, self.ps // 2)
        for x, lane, age in self.trail:
            alpha = get_alpha(x) if get_alpha else 255
            a = int(alpha * max(0.0, 1.0 - age / TRAIL_LIFE) * 0.35)
            if a <= 0:
                continue
            c = apply_tint(QColor(*TRAIL_COLOR), tint)
            c.setAlpha(a)
            painter.fillRect(int(x), int(ground_y - lane), ph, ph, c)


class SkatingScene(BaseScene):
    def __init__(self):
        self.skaters = []
        self.trees = []      # (x, h_units, seed)
        self.stars = []      # (x, y_px_from_top, phase)
        self.flakes = []     # [x, y, spd, phase]
        self.scale = 1.0
        self.ps = PIXEL_SIZE
        self.area_h = 120
        self.ice_h = 24
        self.bank_h = 8
        self.width = 0
        self.avoid = 0
        self.trail_on = True
        self.snow_amount = 40
        self.t = 0
        self._trace_pm = None    # 焼き込み済みの古いトレース層
        self._trace_key = None
        self._trace_seed = 0

    def get_area_height(self, config):
        s = config.get("skate_scale", 100) / 100.0
        return max(110, int(160 * s))

    def rebuild(self, config, screen_width, widget_width):
        self.scale = config.get("skate_scale", 100) / 100.0
        self.ps = max(2, int(PIXEL_SIZE * self.scale))
        self.area_h = self.get_area_height(config)
        self.ice_h = self.ps * 9
        self.bank_h = self.ps * 2
        self.width = widget_width
        self.trail_on = config.get("skate_trail", True)
        self.snow_amount = config.get("skate_snow", 40)
        self.avoid = min(hamburger_avoid_px(self.scale), widget_width)

        seed = config.get("seed", random.randint(0, 999999))
        rng = random.Random(seed ^ 0x5CA7E)
        self._trace_seed = seed
        self._trace_pm = None  # レイアウト変更で焼き込みトレースを作り直す
        self._trace_key = None

        # 背景の針葉樹: 遠景の小さなシルエットに留める（作業の邪魔をしない）
        self.trees = []
        x = self.avoid + rng.randint(0, 80)
        while x < widget_width - 20:
            h = rng.randint(4, 9)
            self.trees.append((x, h, rng.randint(0, 9999)))
            x += rng.randint(110, 300)

        # 星（上部30%で瞬く）
        self.stars = []
        for _ in range(max(4, widget_width // 220)):
            self.stars.append((rng.randint(0, widget_width),
                               rng.randint(2, max(3, int(self.area_h * 0.3))),
                               rng.uniform(0, math.tau)))

        # 雪
        self.flakes = []
        n_flakes = int(widget_width / 60 * (self.snow_amount / 50.0))
        for _ in range(n_flakes):
            self.flakes.append([rng.uniform(0, widget_width),
                                rng.uniform(0, self.area_h),
                                rng.uniform(0.4, 1.1),
                                rng.uniform(0, math.tau)])

        # スケーター: 各自パターンダンスを選び、周回コースの別位置から滑り出す
        count = max(1, min(5, config.get("skate_count", 2)))
        self.skaters = []
        min_x = self.avoid + 6 * self.ps
        max_x = max(min_x + 10, widget_width - 8 * self.ps)
        for i in range(count):
            dance = rng.choice(PATTERN_DANCES)
            s0 = rng.uniform(0, math.tau)
            self.skaters.append(Skater(rng, self.ps, dance, s0, min_x, max_x))

    def _build_trace_pm(self, tint, get_alpha):
        """リンクに刻まれた無数の古いトレースを1枚のピクスマップに焼き込む。
        毎フレームは転送1回で済むため、本数を増やしてもメモリは画像1枚分
        （幅×氷の高さ）で一定、CPUコストもほぼ増えない。
        """
        pm = QPixmap(max(1, self.width), max(1, self.ice_h))
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        rng = random.Random(self._trace_seed ^ 0x7AACE)
        ph = max(1, self.ps // 2)
        for sk in self.skaters:
            # 同じパターンを何周も滑った跡（少しずつズレてかすれる）
            for _rep in range(4):
                jx = rng.uniform(-1.0, 1.0) * self.ps
                jz = rng.uniform(-0.02, 0.02)
                n = 420
                for j in range(n):
                    if rng.random() < 0.25:
                        continue  # 跡の途切れ・かすれ
                    x, z = sk._pattern_pos(j / n * math.tau)
                    z = min(1.0, max(0.0, z + jz))
                    lane = int(self.ice_h * (
                        1.0 - (LANE_FAR + (LANE_NEAR - LANE_FAR) * z)))
                    px = int(x + jx)
                    alpha = get_alpha(px) if get_alpha else 255
                    a = int(alpha * rng.uniform(0.06, 0.16))
                    if a <= 0:
                        continue
                    c = apply_tint(QColor(*TRAIL_COLOR), tint)
                    c.setAlpha(a)
                    p.fillRect(px, self.ice_h - lane, ph, ph, c)
        p.end()
        return pm

    def update(self, wind_sim, mouse_pos=None):
        self.t += 1
        for s in self.skaters:
            wave = wind_sim.get_wave_at(s.x)
            s.update(wave, self.trail_on, self.ice_h)
        # 雪はゆっくり落ち、風で流れる
        for f in self.flakes:
            f[1] += f[2]
            f[3] += 0.02
            w = wind_sim.get_wave_at(f[0])
            f[0] += math.sin(f[3]) * 0.4 + w * 0.25
            if f[1] > self.area_h:
                f[1] = 0.0
                f[0] = random.uniform(0, max(1, self.width))
            if f[0] < 0:
                f[0] += self.width
            elif f[0] > self.width:
                f[0] -= self.width

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        ps = self.ps
        ice_top = ground_y - self.ice_h
        bank_top = ice_top - self.bank_h
        top_y = ground_y - self.area_h

        # 星（瞬き）
        for sx, sy, phase in self.stars:
            alpha = get_alpha(sx) if get_alpha else 255
            a = int(alpha * (0.45 + 0.30 * math.sin(self.t * 0.03 + phase)))
            c = apply_tint(QColor(*STAR_COLOR), tint)
            c.setAlpha(max(0, a))
            painter.fillRect(int(sx), int(top_y + sy), 2, 2, c)

        # 対岸の針葉樹（雪化粧）: 遠景なので半透明の小さなシルエット
        for tx, h, tseed in self.trees:
            alpha = get_alpha(tx) if get_alpha else 255
            alpha_t = int(alpha * 0.55)
            trng = random.Random(tseed)
            for row in range(h):
                # 上ほど細い三角形
                w_units = max(1, int((h - row) * 0.55))
                y = int(bank_top - (row + 1) * ps)
                c = apply_tint(QColor(*TREE_COLOR), tint)
                c.setAlpha(alpha_t)
                painter.fillRect(int(tx - w_units * ps), y,
                                 (w_units * 2 + 1) * ps, ps, c)
                # 枝先の雪
                if trng.random() < 0.30 or row == h - 1:
                    sc = apply_tint(QColor(*TREE_SNOW), tint)
                    sc.setAlpha(int(alpha_t * 0.8))
                    painter.fillRect(int(tx - w_units * ps), y, ps, ps, sc)
                    painter.fillRect(int(tx + w_units * ps), y, ps, ps, sc)

        # 湖岸の雪堤
        seg = 8 * ps
        x = 0
        while x < self.width:
            alpha = get_alpha(x) if get_alpha else 255
            bump = int(math.sin(x * 0.02) * ps * 0.5)
            c = apply_tint(QColor(*BANK_COLOR), tint)
            c.setAlpha(alpha)
            painter.fillRect(x, bank_top - bump, seg, self.bank_h + bump, c)
            x += seg

        # 氷面
        x = 0
        while x < self.width:
            alpha = get_alpha(x) if get_alpha else 255
            c = apply_tint(QColor(*ICE_COLOR), tint)
            c.setAlpha(alpha)
            painter.fillRect(x, ice_top, seg, self.ice_h, c)
            # 氷の上端のハイライト
            e = apply_tint(QColor(*ICE_EDGE), tint)
            e.setAlpha(int(alpha * 0.55))
            painter.fillRect(x, ice_top, seg, max(1, ps // 2), e)
            x += seg

        # 月明かりのきらめき（氷上を流れる光の筋）
        for k in range(3):
            gx = int((self.width * (0.2 + 0.3 * k) +
                      math.sin(self.t * 0.008 + k * 2.1) * self.width * 0.15))
            alpha = get_alpha(gx) if get_alpha else 255
            a = int(alpha * (0.10 + 0.08 * math.sin(self.t * 0.02 + k)))
            c = apply_tint(QColor(*ICE_EDGE), tint)
            c.setAlpha(max(0, a))
            painter.fillRect(gx, ice_top + ps, 14 * ps, self.ice_h - 2 * ps, c)

        # リンクに刻まれた古いトレース（焼き込み済みレイヤーを1回転送）
        if self.trail_on and self.skaters:
            key = (str(tint), self.width, self.ice_h)
            if self._trace_pm is None or self._trace_key != key:
                self._trace_pm = self._build_trace_pm(tint, get_alpha)
                self._trace_key = key
            painter.drawPixmap(0, ice_top, self._trace_pm)

        # トレース → スケーター（奥にいる人から順に描画）
        ordered = sorted(self.skaters, key=lambda s: s.z)
        for s in ordered:
            s.draw_trail(painter, ground_y, tint, get_alpha)
        for s in ordered:
            alpha = get_alpha(s.x) if get_alpha else 255
            s.draw(painter, ground_y, tint, alpha)

        # 雪（最前面）
        fs = max(2, ps // 2)
        for f in self.flakes:
            alpha = get_alpha(f[0]) if get_alpha else 255
            c = apply_tint(QColor(*SNOW_COLOR), tint)
            c.setAlpha(int(alpha * 0.75))
            painter.fillRect(int(f[0]), int(top_y + f[1]), fs, fs, c)
