"""Shark scene - cute pixel sharks cruising in the deep sea

深海をゆったり回遊するサメたちのシーン。
サメのドット絵はユーザー提供の生成AI画像をピクセル単位でトレースした134×76マップ。
- サメ: 丸みのあるかわいいシルエット。水の物理（慣性・抵抗）と
  1/fゆらぎで上下にたゆたいながら回遊する。奥行きで縮小＋青く霞む（空気遠近法の水中版）
- 珊瑚: 枝分かれをランダムウォークで生成。手前は彩色、奥は青いシルエット
- 海藻: バネ＋抵抗の水中物理でゆらめく緑の帯
- マリンスノー: 白い粒が左右に舞いながらゆっくり沈み、海底に届くと消える
- 泡: サメの鼻先や海藻から時々立ちのぼる
"""
import math
import random
from scenes.base import BaseScene, PinkNoiseGenerator, PIXEL_SIZE, apply_tint, hamburger_avoid_px
from PyQt5.QtGui import QColor, QPixmap, QPainter, QTransform
from PyQt5.QtCore import Qt, QRect


# --- サメのドット絵（参考画像のピクセル単位トレース、134×76、右向き） ---
# o=輪郭・目, g=暗い線・エラ, D=深い陰, d=陰, b=浅い陰, B=体のベース,
# L=ハイライト, S=淡青(背の光・腹の縁), W=腹の白・目の光, t=歯
SHARK_PALETTE = {
    "o": (27, 61, 104),
    "g": (47, 86, 127),
    "D": (69, 109, 151),
    "d": (85, 132, 175),
    "b": (100, 146, 187),
    "B": (116, 162, 203),
    "L": (139, 189, 222),
    "S": (187, 217, 235),
    "W": (231, 246, 250),
    "t": (174, 170, 180),
}
SHARK_ART = [
    "......................................................bddddddddd......................................................................",
    ".....................................................bgoooooooogDBB...................................................................",
    "....................................................DoDBBBBBBBBdgggb..................................................................",
    "....................................................ggbBBBBLLLLLLBBggd................................................................",
    "....................................................ggbBBBBBBLLLLLLBgDo...............................................................",
    "....................................................dgDdBBBBBBBBLLLLLLgDD.............................................................",
    ".....................................................DgdbbBBBBBBBBLLLLLdgDB...........................................................",
    "......................................................DgddbBBBBBBBBBLLLLLdD...........................................................",
    "......................................................bggddbBBBBBBBBBLLLLLDD..........................................................",
    ".......................................................bodddbBBBBBBBBBLLLLLDD.........................................................",
    "........................................................gDdddbBBBBBBBBBLLLLLdg........................................................",
    "........................................................boddddbBBBBBBBBBLLLLLDg.......................................................",
    "........................................................bodddddbBBBBBBBBBBLLLLdg......................................................",
    "........................................................dodddddbBBBBBBBBBBLLLLLdg.....................................................",
    ".........................................................dodddddbBBBBBBBBBBLLLLLdD....................................................",
    ".........................................................BodddddbBBBBBBBBBBLLLLLLbDggggggggggggggggggggd..............................",
    ".........................................................BoddddddbBBBBBBBBBBBLLLLLBbbbbbbbbbbbbbbbbbbbbggggggD........................",
    ".........................................................BodddddddbBBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLLSSSSBdddddoDDDDd...................",
    "...DDDd..................................................BodddddddbBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLLLLLLLLSSSSSbddDgoDdd................",
    "..Dggggd.................................................BodddddbdddBBBBBLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLSSSSSLdgggDdd.............",
    ".DdLLLgoDd...............................................LodbddddddbBBLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLdggodb...........",
    "gDBLLLLBgod..............................................BodddbdbbLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLSSLLBgodBB........",
    "gDbBBBLLLggb.............................................LodbddbBLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLSSSSBgood.......",
    "gDbBBBLLLBggB............................................DodbBLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLSLLBBgg......",
    "gDbBBBBBLLLDg..........................................LbodBLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLdg.....",
    "gDdBBBBBBLLLDgb.......................................DogbLLLLLLLLLLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLLLLLLLDg....",
    "bgDBBBBBBLLLBgg.....................................bggdbLLLLLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLLLLLLLLgo...",
    ".DDBBBBBBBLLLBDg..................................DDggbBLLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLBgd..",
    ".DgdbBBBBBBLLLdod................DDDd...........dDggdBLLLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLLLLLLLLLLbDd.",
    ".bggbBBBBBBBBLBDob..............gogDgDb......ddDogBBLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLBLLLLbgB",
    "..dgdBBBBBBBBLLLDoB............DoDLLbDgb...bbgogdBLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBLLLBBBBBLLLdgB",
    "..bgDdBBBBBBBBLLdob............DgbBLLLDgbbDogDBLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdgB",
    "...dodBBBBBBBBBLLDgB...........DgdbBLLLDoooDLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdoB",
    "...dodBBBBBBBBBLLbob...........ggddbdbbbLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdoB",
    "....DgdbBBBBBBBLLLDg......BBBBgogDdbbBLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdgB",
    "....BodbBBBBBBBBBLBoD....DooooobBBBBBLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdgB",
    "....BoddBBBBBBBBBBLBgggggdbbbbbLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdgB",
    "....BgDdBBBBBBBBBBBBbddddBLLLLLLLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBbbBBBBBBBBBBBBBBBBBBBbDgB",
    ".....bodBBBBBBBBBBBBBBBBLLLLLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBgooobBBBBBBBBBBBBBBBBBdDd.",
    ".....BoDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdooDbdbBBBBBBBBBBBBBBLLDD..",
    "......gDbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBbBBBBBBBBBBBdoootSoDBBBBBBBBBBBLLLWWDD..",
    ".......gDbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDdBBBBBBBBBBdoooooodBBBBBBBBBLSWWWWLgD..",
    "......LgDbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBbBBBDdBBBBBBBBBBbgooooodBBBBBBBLSWWWWWWgD...",
    "......BgDbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDbBBDdBBBBBBBBBBBBgoogbBBBBBBLWWWWWWWWLgd...",
    "......BgDbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdDdBBbDbBBdDdBBBBBBBBBBBBbbbBBBBBSWWWWWWWWWWDD....",
    ".......oDbBBBBBBBBbdbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdDDBBbDbBBbDDBBBBBBBBBBBBBBBBLSSSWWWWWWWWWWSod....",
    "......DDdbBBBBBBBbdddbbbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdDdBBbDDbBBdgdBBBBBBBBBBBBLSSWWWWWWWWWWWWWWBg.....",
    ".....BoDbBBBBBBBBdddddddbbbbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDDBBBdgbBBbDDBBBBBBBbBLSSWWWWWWWWWWWWWWWWBoD.....",
    ".....BodBBBBBBBBbdddddddddddbbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdDbBBBDDBBBbggBBBBLSSSWWWWWWWWWWWWWWWWWWtog......",
    ".....bodBBBBBBBBbdddDDDdddddddbbbbbbbbbbbbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBbgDBBBbgbBBbbBSSSSWWWWWWWWWSSSSSSSSSSSStgg.......",
    "....BoDbBBBBBBBbdddDoggDDDddddddddddddddddbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdgDBBBdBLLSWWWWWWWWWWWSSSSttttttttttttDD........",
    "....BodBBBBBBBbdddoob..DoogDddbddddddddddddddddddbBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBbbBdgDBBLSWWWWWWWWWWWWWWWttttSWWttWWWtWWWgD........",
    "....bodBBBBBBbddDoob....BdooDdddddddddddddddddddddddddddbBBBBBBBbdbBBBBBBBBBBBBBBBdDdBBLLSWWWWWWWWWWWWWWWWWWWWStttttttWttSWDd.........",
    "...doDbBBBBBbddDooB.......bbggDdddddddddddddddddddddddddddddddddgDbBBBBBBBBBBBBBBdDdBSSWWWWWWWWWWWWWWWWWWWWWWWWWStSWttttttgD..........",
    "...doddBBBBbdddDoD..........bboooDdddddddddddddddddddddddddddddDgDBBBBBBBBBBBBBBbdDBWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWSStoD...........",
    "..dgoddBBBbdddDooB............dbgoooDddddddddddddddddddddddDdddggdBBBBBBBBBBBBBBbdoSWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWSLboD............",
    "..dodddddddddDogb...............BddDggggDddBLLLLLLLLLSSSSSSSSSboDbBBBBBBBBBBBBBbddotWWWWWWWWWWWWWWWWWWWWWWWWWWWWWSSSLLDoD.............",
    "..dgddddddddDog.....................ddDoogdBSSSSSSSSSSWSSWWWWWboDbBBBBBBBBBBBBBddbotWWWWWWWWWWWWWWWWWWWWWWWWWWWWSSSSBggd..............",
    "..dgdddddddDog.........................DDDDDdbLSSSSSSSSSSSSSSSDgdBBBBBBBBBBBBBbddodSWWWWWWWWWWWWWWWWWWWWWWWWWWSSSSSdDDd...............",
    "..DgddddddDog.............................dggDDdbSSSSSSSSSSSSDodbBBBBBBBBBBBBdddDoLWWWWWWWWWWWWWWWWWWWWWWWSSSSSSSdDDd.................",
    "..dgDddddDood.................................gggDbBBLSSSSSSSggdbBBBBBBBBBBBbddDogSSWWWWWWWWWWWWWWWSSSSSSSSSSSLDgoD...................",
    "...DodddDood....................................BooooDLLLLLSooDbBBBBBBBBBBBbdddgoSSSSSSSSSSSSSSSSSSSSSSSSSSSbbgood....................",
    "...Dooooodd......................................BBBBdooooodoDdBBBBBBBBBBBbdddgodSSSSSSSSSSSSSSSSSSSSSSSLbddoooBb.....................",
    "....ddddd.............................................BBBBBooDdBBBBBBBBBBbdddDoDSSSSSSSSSSSSSSSSSSSSSSLBgooobbb.......................",
    "..........................................................BoodbBBBBBBBBBbbddDogSSSSSSSSSSSSSSSSSSSLoooooDbbb..........................",
    "..........................................................goDdbBBBBBBBBbdddDoogggggggggggggggggggggDbddd..............................",
    ".........................................................booddbBBBBBBbddddDogbbbddddddgoogDDDDDDgog...................................",
    ".........................................................goDddbBBBBbdddddDog..........DogDddddddDgb...................................",
    "........................................................doDdddddbbddddddgog...........DodddddddDgd....................................",
    "........................................................Doddddddddddddgggg............DoddddddDgd.....................................",
    ".......................................................DoDdddddddddddgogb.............DgddddDgoD......................................",
    ".......................................................DgbdddddddddDgoD...............DgDDDDooD.......................................",
    ".......................................................DoddddddddDDogd.................DooooDd........................................",
    ".......................................................DogdddddgoooD....................dddd..........................................",
    "........................................................DoooooooDbb...................................................................",
    ".........................................................DDddddd......................................................................",
]
SHARK_W = len(SHARK_ART[0]) if SHARK_ART else 0
SHARK_H = len(SHARK_ART)
TAIL_COL = 22       # この列より左（原画）が尾ビレ＝揺れに連動
SWAY_AMP = 4.0      # 尾ビレ先端の揺れ幅（ドット）
N_FRAMES = 8        # 尾ビレ揺れの焼き込みフレーム数

SHARK_DOTS = [(c, r, ch) for r, row in enumerate(SHARK_ART)
              for c, ch in enumerate(row) if ch in SHARK_PALETTE]

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
        # 個体差: わずかな明度差＋奥行きの霞（青フィルタ）をパレットに焼き込む
        # 奥行きはアルファ透過を使わず「縮小＋青く霞む」だけで表現する
        bright = rng.choice([0.93, 1.0, 1.06])
        self.palette = {}
        for ch, col in SHARK_PALETTE.items():
            hz = _haze(col, depth, 0.75)
            self.palette[ch] = tuple(min(255, int(v * bright)) for v in hz)
        self.frames = None          # [(右向きQPixmap, 左向きQPixmap), ...]
        self._baked_tint = None
        self.direction = rng.choice([-1, 1])
        self.target_dir = self.direction
        self.vx = self.speed * self.direction
        self.vy = 0.0
        self.swim_phase = rng.uniform(0, math.tau)
        self.noise_y = PinkNoiseGenerator()
        self.think = rng.randint(200, 700)
        self.vy_force = 0.0

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
        margin = 200
        if self.x > width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = width + margin

    def _bake(self, tint):
        """尾ビレ揺れ N_FRAMES 枚×左右向きを QPixmap に焼き込む。
        ドット数が多い（約5500）ため毎フレームの個別描画はせず、
        描画時は drawPixmap 1回の転送のみ（スケート軌跡と同方式）。
        """
        pad = int(SWAY_AMP) + 2
        flip = QTransform().scale(-1, 1)
        self.frames = []
        for f in range(N_FRAMES):
            sway = math.sin(math.tau * f / N_FRAMES) * SWAY_AMP
            # 列ごとのシフト量（尾ビレは付け根k=0から先端k=1ほど大きく揺れる）
            shifts = [int(round(sway * (TAIL_COL - c) / TAIL_COL))
                      if c < TAIL_COL else 0 for c in range(SHARK_W + 1)]
            pm = QPixmap(SHARK_W + pad * 2, SHARK_H)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            for c, r, ch in SHARK_DOTS:
                # 隣の列とシフト量が1ずれて隙間（縦線）ができないよう、
                # 伸びる側はドット幅を広げて埋める
                w = 1 + max(0, shifts[c + 1] - shifts[c])
                p.fillRect(c + pad + shifts[c], r, w, 1,
                           apply_tint(QColor(*self.palette[ch]), tint))
            p.end()
            self.frames.append((pm, pm.transformed(flip)))
        self._baked_tint = tint

    def draw(self, painter, alpha, tint, ps):
        if self.frames is None or tint != self._baked_tint:
            self._bake(tint)
        idx = int(self.swim_phase / math.tau * N_FRAMES) % N_FRAMES
        pm = self.frames[idx][0 if self.direction > 0 else 1]
        scale = (ps / float(PIXEL_SIZE)) * (1.0 - self.depth * 0.45)
        w = max(1, int(pm.width() * scale))
        h = max(1, int(pm.height() * scale))
        rect = QRect(int(self.x - w / 2), int(self.y - h / 2), w, h)
        painter.setOpacity(alpha / 255.0)
        # 等倍以外の拡縮で最近傍サンプリングの列落ち（縞）が出ないよう
        # スムーズ変換で転送する
        smooth = painter.testRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(rect, pm)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, smooth)
        painter.setOpacity(1.0)


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


# --- 沈没船（レック） ---
# 大戦期の艦影をイメージした半ば砂に埋もれた残骸。船体には破孔、マストは折れている。
# 奥のシルエットとして描き、底層流がぶつかって生まれる湧昇流（噴出）が
# マリンスノーを巻き上げる「人工の主」となる
WRECK_PALETTE = {
    "o": (26, 42, 64),     # 輪郭
    "g": (38, 54, 76),     # マスト・砲・暗部
    "d": (46, 64, 86),     # 陰
    "B": (64, 84, 106),    # 船体ベース
    "L": (84, 106, 128),   # 上縁のわずかな光
    "c": (96, 90, 110),    # 付着した珊瑚・錆のアクセント
}
# 戦艦（巨大レック。湧昇流の主・魚礁の核）
BATTLESHIP_ART = [
    "..........g...........................................",
    "..........g................c..........................",
    ".........gg.............ooo...........................",
    ".........gg.c...........oBdo..........................",
    "........ogg.........ooooLBBdo.........................",
    ".......oBggooooooooooLLLBBBBdoo................c......",
    ".......oBBBBBBBBBBBBBBBBBBBBBBdoo.............oo......",
    "....oooLBBBBBBBBBBBBBBBBBBBBBBBBdoo.........ooLo......",
    "...oLBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdooo....ooBBLo......",
    "..oBBBBBBBB..oBBBBBBBBBBB..BBBBBBBBBBdoooooBBBBo......",
    "..oBBBBBBB....BBBBBBBBBB....BBBBBBBBBBBBBBBBBBo.......",
    "..odBBBBBBB..BBBBBBBBBBBB..BBBBBBBBBBBBBBBBBBo........",
    "...odBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBo.........",
    "....oddddBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBdo..........",
    "......oodddddddddddddddddddddddddddddddddoo...........",
    ".........ooooooooooooooooooooooooooooooo..............",
]
# 沈没船（中型の貨物船。船室と破孔）
BOAT_ART = [
    "..............ooo......................",
    "..............oBdo..........c..........",
    ".........ooooooBBdoooo.................",
    ".........oBBBBBBBBBBdo.................",
    ".....c...oBBB..BBBBBdo.................",
    ".....ooooBBBBBBBBBBBBooooooo...........",
    "....oLBBBBBBBBBBBBBBBBBBBBBdo..........",
    "....oBBBBBB..dBBBBBBBBBBBBBdo..........",
    ".....oBBBBBBBBBBBBBBBBddddddo..........",
    "......oddddddddddddddddddoo............",
    ".......oooooooooooooooooo..............",
]
# 航空機の残骸（大戦機。片翼を立てて尾部は折れている）
PLANE_ART = [
    "..........oo......................",
    ".........oLBo.....................",
    ".........oBBo.....................",
    "........oBBo......................",
    "........oBBo...........c..........",
    ".......oBBo.................oo....",
    "o......oBBo................oBo....",
    "oo....oBBBo..............ooBBo....",
    "oBooooBBBBBoooooooooooooBBBBo.....",
    "oBBBBBBBB..BBBBBBBBBBBBBBBdo......",
    ".ooBBBBBBBBBBBdddddddddddoo.......",
    "...ooodddddoooooooooooooo.........",
]
BATTLESHIP_W = max(len(row) for row in BATTLESHIP_ART)


class Wreck:
    def __init__(self, rng, base_x, depth, art):
        self.base_x = base_x        # 左端
        self.depth = depth
        self.art_w = max(len(row) for row in art)
        self.art_h = len(art)
        self.dots = [(c, r, ch) for r, row in enumerate(art)
                     for c, ch in enumerate(row) if ch in WRECK_PALETTE]
        self.flip = rng.random() < 0.5
        self.palette = {ch: QColor(*_haze(col, depth, 0.5))
                        for ch, col in WRECK_PALETTE.items()}
        # 構造物の大きさに応じた湧昇流の強さ係数（巨大な主ほど強い）
        self.flow_k = min(1.2, self.art_w / float(BATTLESHIP_W))

    def px_size(self, ps):
        return max(1, int(ps * (1.0 - self.depth * 0.35)))

    def width_px(self, ps):
        return self.art_w * self.px_size(ps)

    def center_x(self, ps):
        return self.base_x + self.width_px(ps) / 2.0

    def draw(self, painter, ground_y, alpha, tint, ps):
        ps = self.px_size(ps)
        a = int(alpha * 0.8)
        for c, r, ch in self.dots:
            col = apply_tint(QColor(self.palette[ch]), tint)
            col.setAlpha(a)
            cx = (self.art_w - 1 - c) if self.flip else c
            painter.fillRect(int(self.base_x + cx * ps),
                             int(ground_y - (self.art_h - r) * ps), ps, ps, col)


# --- 小魚の群れ（人工魚礁=沈没船に集まるボイド） ---
FISH_COLOR = (172, 198, 216)
FISH_DARK = (118, 150, 178)


class Fish:
    def __init__(self, rng, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = rng.uniform(-0.4, 0.4)
        self.vy = rng.uniform(-0.15, 0.15)
        self.phase = rng.uniform(0, math.tau)
        self.g = 1.0   # 群れの「呼吸」係数（散開0.2〜密集2.0）のキャッシュ


class FishSchools:
    """局所ボイドの魚群。
    近くの仲間とだけ結束・整列するため、群れ同士が出会えば合流し、
    サメに裂かれたり別のアンカーに引かれたりすると自然に分裂する。
    群れの「気分」となる漂遊アンカーが横方向に広く回遊し、
    群れは追従しながら伸びたり広がったり形を変える"""

    SIGHT = 50.0        # 仲間と認識する視界
    MAX_FISH = 150

    def __init__(self, rng, n_schools, base_size, width, area_h,
                 reef_x=None, depth=0.5):
        self.width = width
        self.area_h = area_h
        self.reef_x = reef_x
        self.depth = depth
        self.color = QColor(*_haze(FISH_COLOR, depth, 0.6))
        self.dark = QColor(*_haze(FISH_DARK, depth, 0.6))
        self.t = rng.uniform(0, 1000)
        self.fish = []
        self.anchors = []   # [x, y, noise, vx, phase]
        total = 0
        for _ in range(n_schools):
            # 群れの大きさは基準の前後（0.5〜1.6倍）でランダム
            size = max(4, int(base_size * rng.uniform(0.5, 1.6)))
            size = min(size, self.MAX_FISH - total)
            if size <= 0:
                break
            total += size
            # 魚礁（最大の沈没物）の周辺に発生
            cx = reef_x if reef_x is not None else width * 0.5
            ax = cx + rng.uniform(-width * 0.15, width * 0.15)
            ax = min(max(ax, width * 0.08), width * 0.92)
            ay = rng.uniform(area_h * 0.30, area_h * 0.65)
            self.anchors.append([ax, ay, PinkNoiseGenerator(),
                                 rng.uniform(-0.3, 0.3),
                                 rng.uniform(0, math.tau),
                                 rng.uniform(0, math.tau),   # 呼吸の位相
                                 PinkNoiseGenerator()])      # 呼吸のゆらぎ
            for _ in range(size):
                self.fish.append(Fish(rng, ax + rng.uniform(-45, 45),
                                      ay + rng.uniform(-28, 28)))

    def update(self, sharks, ps, min_y, max_y):
        self.t += 1
        fs = self.fish
        if not fs:
            return
        # アンカー: 1/fゆらぎで横に大きく回遊。時々魚礁の上空に戻ってくる
        for a in self.anchors:
            a[3] += a[2].next() * 0.03
            # 魚礁が行動圏の中心: 離れるほど強く引き戻される
            if self.reef_x is not None:
                a[3] += (self.reef_x - a[0]) * 0.00004
            a[3] = max(-0.7, min(0.7, a[3]))
            a[0] += a[3]
            if a[0] < self.width * 0.06:
                a[0] = self.width * 0.06
                a[3] = abs(a[3])
            elif a[0] > self.width * 0.94:
                a[0] = self.width * 0.94
                a[3] = -abs(a[3])
            a[1] += math.sin(self.t * 0.004 + a[4]) * 0.06
            a[1] = min(max(a[1], self.area_h * 0.2), self.area_h * 0.75)
        # 群れの「呼吸」: 1/fゆらぎでゆっくり散開⇄密集を繰り返す
        gathers = []
        for a in self.anchors:
            b = 0.5 + 0.5 * math.sin(self.t * 0.005 + a[5]) + a[6].next() * 0.4
            gathers.append(0.2 + min(max(b, 0.0), 1.0) * 1.8)
        # 局所ボイド: 視界内の仲間とだけ結束・整列・分離
        sight = self.SIGHT
        r2 = sight * sight
        n = len(fs)
        for i in range(n):
            fi = fs[i]
            for j in range(i + 1, n):
                fj = fs[j]
                dx = fi.x - fj.x
                if dx > sight or dx < -sight:
                    continue
                dy = fi.y - fj.y
                d2 = dx * dx + dy * dy
                if d2 < r2:
                    # 結束（呼吸係数で強弱: 散開時はゼロまで落ちて広がれる）
                    gavg = (fi.g + fj.g) * 0.5
                    co = max(0.0, gavg - 0.5) * 0.0005
                    fi.vx -= dx * co
                    fi.vy -= dy * co
                    fj.vx += dx * co
                    fj.vy += dy * co
                    # 整列: 速度をならす → 群れ全体のうねる動き
                    # （散開時は同調を弱め、各自ばらばらに泳いで広がる）
                    al = 0.003 + 0.017 * min(1.0, max(0.0, gavg - 0.5))
                    mvx = (fi.vx + fj.vx) * 0.5
                    mvy = (fi.vy + fj.vy) * 0.5
                    fi.vx += (mvx - fi.vx) * al
                    fi.vy += (mvy - fi.vy) * al
                    fj.vx += (mvx - fj.vx) * al
                    fj.vy += (mvy - fj.vy) * al
                    if 0 < d2 < 64:
                        push = 0.03 / max(1.0, d2 / 16.0)
                        fi.vx += dx * push
                        fi.vy += dy * push
                        fj.vx -= dx * push
                        fj.vy -= dy * push
        # 最寄りのアンカーへ弱く引かれる（アンカーが交差すると群れが入れ替わる）
        for f in fs:
            best = None
            bd = 1e18
            bg = 1.0
            for a, g in zip(self.anchors, gathers):
                dx = a[0] - f.x
                dy = a[1] - f.y
                d2 = dx * dx + dy * dy
                if d2 < bd:
                    bd = d2
                    best = a
                    bg = g
            f.g = bg
            f.vx += (best[0] - f.x) * 0.0005 * bg
            f.vy += (best[1] - f.y) * 0.0008 * bg
            # 散開フェーズ（bg小）はアンカーから外向きにふわっと広がる
            if bg < 0.8 and bd < 32400:   # 半径180px まで
                out = (0.8 - bg) * (1.0 - bd / 32400.0)
                f.vx += (f.x - best[0]) * 0.0011 * out
                f.vy += (f.y - best[1]) * 0.0007 * out
            f.vx += math.sin(self.t * 0.03 + f.phase) * 0.012
            f.vy += math.sin(self.t * 0.025 + f.phase * 1.7) * 0.006
        # 天敵（サメ）から逃げる → 群れが割れる
        for s in sharks:
            k = 1.0 - s.depth * 0.45
            r = SHARK_W * 0.8 * (ps / float(PIXEL_SIZE)) * k
            sr2 = r * r
            for f in fs:
                dx = f.x - s.x
                dy = f.y - s.y
                d2 = dx * dx + dy * dy
                if d2 < sr2:
                    d = math.sqrt(d2) or 1.0
                    fl = (1.0 - d / r) * 0.25
                    f.vx += dx / d * fl
                    f.vy += dy / d * fl
        margin = (max_y - min_y) * 0.18
        for f in fs:
            # 上下の境界手前からソフトに押し返す（張り付いて線にならない）
            if f.y < min_y + margin:
                f.vy += (min_y + margin - f.y) * 0.004
            elif f.y > max_y - margin:
                f.vy -= (f.y - (max_y - margin)) * 0.004
            sp = math.hypot(f.vx, f.vy)
            if sp > 1.8:
                f.vx *= 1.8 / sp
                f.vy *= 1.8 / sp
            f.vx *= 0.985
            f.vy *= 0.985
            f.x += f.vx
            f.y += f.vy
            if f.y < min_y:
                f.y = min_y
                f.vy = abs(f.vy) * 0.5
            elif f.y > max_y:
                f.y = max_y
                f.vy = -abs(f.vy) * 0.5
            if f.x < 2:
                f.x = 2
                f.vx = abs(f.vx)
            elif f.x > self.width - 2:
                f.x = self.width - 2
                f.vx = -abs(f.vx)

    def draw(self, painter, a_at, tint, ps):
        s = max(1, int(ps * (1.0 - self.depth * 0.35)))
        body = apply_tint(QColor(self.color), tint)
        tail = apply_tint(QColor(self.dark), tint)
        for f in self.fish:
            a = a_at(f.x)
            body.setAlpha(int(a * 0.85))
            tail.setAlpha(int(a * 0.8))
            d = 1 if f.vx >= 0 else -1
            painter.fillRect(int(f.x), int(f.y), s * 2, s, body)
            painter.fillRect(int(f.x) - d * s, int(f.y), s, s, tail)


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


# --- マリンスノー（左右に舞いながらゆっくり沈む白い粒） ---
class SnowFleck:
    def __init__(self, rng, width, area_h, ps, at_top=False):
        self.x = rng.uniform(0, max(1, width))
        self.y = rng.uniform(-10, 0) if at_top else rng.uniform(0, area_h)
        self.vy = rng.uniform(0.06, 0.20)
        self.phase = rng.uniform(0, math.tau)
        self.sway = rng.uniform(0.1, 0.35)
        self.size = max(1, ps // 2) * rng.choice([1, 1, 1, 2])
        self.alpha = rng.randint(50, 120)
        # サメの通過などで受ける流れ（減衰しながら漂う）
        self.dvx = 0.0
        self.dvy = 0.0

    def update(self, t):
        self.y += self.vy + self.dvy
        self.x += math.sin(t * 0.01 + self.phase) * self.sway + self.dvx
        self.dvx *= 0.95
        self.dvy *= 0.95

    def draw(self, painter, bottom_y):
        # 海底に近づくと薄れて消える
        fade = max(0.0, min(1.0, (bottom_y - self.y) / 20.0))
        a = int(self.alpha * fade)
        if a > 0:
            painter.fillRect(int(self.x), int(self.y), self.size, self.size,
                             QColor(214, 230, 240, a))


# --- SharkScene ---
class SharkScene(BaseScene):
    def __init__(self):
        self.sharks = []
        self.corals = []
        self.seaweeds = []
        self.bubbles = []
        self.snow = []
        self.wrecks = []
        self.wreck_flow = 80
        self.schools = None
        self.terrain = []
        self.bubble_timer = 0
        self.width = 0
        self.area_h = 200
        self.scale = 1.0
        self.ps = PIXEL_SIZE
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

        # 沈没物（ジャンルごとに配置。噴出=湧昇流の強さは設定値）
        self.wreck_flow = config.get("shark_wreck_flow", 80)
        self.wrecks = []

        def place_wreck(art):
            depth = rng.uniform(0.5, 0.65)
            w_px = max(len(r) for r in art) \
                * max(1, int(self.ps * (1.0 - depth * 0.35)))
            lo = avoid
            hi = max(lo + 1, widget_width - w_px - 10)
            self.wrecks.append(Wreck(rng, rng.randint(lo, hi), depth, art))

        if config.get("shark_wreck", True):                  # 戦艦（巨大）
            place_wreck(BATTLESHIP_ART)
        for _ in range(config.get("shark_wreck_boats", 1)):  # 沈没船（中型）
            place_wreck(BOAT_ART)
        for _ in range(config.get("shark_wreck_planes", 1)):  # 航空機の残骸
            place_wreck(PLANE_ART)

        # 小魚の魚群（群れの数は設定、大きさは基準の前後ランダム。
        # 魚礁=最大の沈没物の周辺に時々戻ってくる）
        fish_base = max(0, min(60, config.get("shark_fish", 30)))
        n_schools = max(1, min(6, config.get("shark_fish_schools", 2)))
        self.schools = None
        if fish_base > 0:
            reef_x = None
            if self.wrecks:
                reef = max(self.wrecks, key=lambda w: w.art_w)
                reef_x = reef.center_x(self.ps)
            self.schools = FishSchools(rng, n_schools, fish_base,
                                       widget_width, self.area_h, reef_x)

        # 海底の起伏: なだらかな丘のうねり＋ゴツゴツの乱れ＋時々大きな隆起
        self.terrain = []
        phase = rng.uniform(0, math.tau)
        phase2 = rng.uniform(0, math.tau)
        jag = 0.0
        v = 0.0
        ridge = 0.0
        for i in range(widget_width // self.ps + 2):
            v += rng.uniform(-0.5, 0.5)
            v *= 0.85
            jag = max(-2.0, min(2.0, jag + v))
            if ridge > 0:
                ridge -= rng.uniform(0.1, 0.4)
            elif rng.random() < 0.012:
                ridge = rng.uniform(3.0, 7.0)    # 隆起の始まり
            swell = 2.5 * math.sin(i * 0.035 + phase) \
                + 1.5 * math.sin(i * 0.011 + phase2)
            h = 3.5 + swell + jag + max(0.0, ridge)
            self.terrain.append(max(1, min(12, int(h))))

        # マリンスノー（最初から水中全体に分布。量は設定で0〜400%）
        snow_amount = config.get("shark_snow", 100)
        n_snow = int(max(10, widget_width // 25) * snow_amount / 100.0)
        self.snow = [SnowFleck(rng, widget_width, self.area_h, self.ps)
                     for _ in range(n_snow)]
        self.bubbles = []

    def update(self, wind_sim, mouse_pos=None):
        self.t += 1
        for s in self.sharks:
            s.update(self.width)
        for w in self.seaweeds:
            w.update(wind_sim.get_wave_at(w.base_x))
        floor_y = self.area_h - 2 * self.ps
        if self.schools:
            self.schools.update(self.sharks, self.ps,
                                int(self.area_h * 0.12),
                                floor_y - self.ps)
        # サメの排水流: 近くの粒を進行方向へ押し流し＋体から外へ押しのける。
        # 海底近くを通ると砂上の雪が巻き上がって舞う
        for s in self.sharks:
            if abs(s.vx) < 0.05:
                continue
            k = 1.0 - s.depth * 0.45
            r = SHARK_W * 0.7 * (self.ps / float(PIXEL_SIZE)) * k
            r2 = r * r
            for f in self.snow:
                dx = f.x - s.x
                dy = f.y - s.y
                d2 = dx * dx + dy * dy
                if d2 < r2:
                    d = math.sqrt(d2) or 1.0
                    fall = (1.0 - d / r) ** 2
                    spd = abs(s.vx)
                    # 進行方向への引き込み＋放射状の押しのけ＋わずかな揚力
                    f.dvx += s.vx * 0.8 * fall + (dx / d) * spd * 0.35 * fall
                    f.dvy += (dy / d) * spd * 0.35 * fall - spd * 0.12 * fall
        # 沈没物の湧昇流（噴出）: 底層流が構造物にぶつかり、上の雪柱を巻き上げる。
        # 構造物が大きいほど強い（flow_k）
        if self.wrecks and self.wreck_flow > 0:
            strength = self.wreck_flow / 100.0
            for w in self.wrecks:
                cx = w.center_x(self.ps)
                half = w.width_px(self.ps) * 1.1
                st = strength * w.flow_k
                for f in self.snow:
                    ddx = f.x - cx
                    if abs(ddx) < half:
                        k = (1.0 - abs(ddx) / half) ** 2
                        # 海底に近いほど強いが、中層でも柱として立ちのぼる
                        deep = 0.3 + 0.7 * max(0.0, min(
                            1.0, f.y / max(1, floor_y)))
                        pulse = 0.6 + 0.4 * math.sin(self.t * 0.02 + f.phase)
                        f.dvy -= 0.08 * st * k * deep * pulse
                        # 立ちのぼりながら左右に揺らぐ（流体のうねり）
                        f.dvx += math.sin(self.t * 0.015 + f.y * 0.04) \
                            * 0.03 * st * k
        for i, f in enumerate(self.snow):
            f.update(self.t)
            if f.y > floor_y or f.y < -12:
                # 海底に届いた／湧昇流で画面上端を越えたら水面から降り直す
                self.snow[i] = SnowFleck(random, self.width, self.area_h,
                                         self.ps, at_top=True)
        if self.bubbles_on:
            self.bubble_timer += 1
            if self.bubble_timer % 30 == 0:
                if self.sharks and random.random() < 0.5:
                    s = random.choice(self.sharks)
                    k = 1.0 - s.depth * 0.45
                    nose = s.x + 15 * s.direction * self.ps * k
                    self.bubbles.append(
                        Bubble(nose, s.y + 2 * self.ps * k, self.ps))
                elif self.wrecks and random.random() < 0.4:
                    # 残骸の破孔から時々泡が漏れる
                    w = random.choice(self.wrecks)
                    bx = w.base_x + random.uniform(0.2, 0.8) * w.width_px(self.ps)
                    self.bubbles.append(Bubble(
                        bx, self.area_h - w.art_h * 0.6 * w.px_size(self.ps),
                        self.ps))
                elif self.seaweeds:
                    w = random.choice(self.seaweeds)
                    self.bubbles.append(Bubble(
                        w.base_x, self.area_h - w.height * self.ps, self.ps))
            for b in self.bubbles:
                b.update()
            self.bubbles = [b for b in self.bubbles if b.alive and b.y > -10]
            if len(self.bubbles) > 40:
                self.bubbles = self.bubbles[-40:]

    def has_background_layer(self):
        # 海底地形はウィンドウの後ろに回り込む
        return True

    def draw_background(self, painter, ground_y, tint=None, get_alpha=None):
        ps = self.ps
        # 海底: 起伏のある地形（丘・隆起・ゴツゴツの岩肌）。背面レイヤーに描く
        sand = apply_tint(QColor(*SAND_COLOR), tint)
        sand.setAlpha(150)
        crest = apply_tint(QColor(*SAND_COLOR), tint)
        crest = QColor(min(255, crest.red() + 24),
                       min(255, crest.green() + 22),
                       min(255, crest.blue() + 20), 160)
        dark = apply_tint(QColor(*SAND_DARK), tint)
        dark.setAlpha(140)
        srng = random.Random(1234)
        for i, h in enumerate(self.terrain):
            x = i * ps
            # マウス接近フェード（列ごと）
            k = (get_alpha(x) / 255.0) if get_alpha else 1.0
            shade = h >= 3 and srng.random() < 0.35
            row = srng.randint(1, h - 1) if shade else 0
            if k <= 0.01:
                continue
            sand.setAlpha(int(150 * k))
            crest.setAlpha(int(160 * k))
            painter.fillRect(x, ground_y - h * ps, ps, h * ps, sand)
            painter.fillRect(x, ground_y - h * ps, ps, ps, crest)  # 上縁の光
            # 斜面・岩肌の陰影
            if shade:
                dark.setAlpha(int(140 * k))
                painter.fillRect(x, ground_y - row * ps, ps, ps, dark)

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        ps = self.ps
        # 奥の珊瑚・海藻 → 奥のサメ → 手前の珊瑚・海藻 → 手前のサメ
        def a_at(x):
            return get_alpha(int(x)) if get_alpha else 255

        # 沈没物（最奥のシルエット）
        for w in self.wrecks:
            w.draw(painter, ground_y, a_at(w.center_x(ps)), tint, ps)
        for c in self.corals:
            if c.depth > 0.5:
                c.draw(painter, ground_y, a_at(c.base_x), tint, ps)
        for w in self.seaweeds:
            if w.depth > 0.5:
                w.draw(painter, ground_y, a_at(w.base_x), tint, ps)
        for s in sorted(self.sharks, key=lambda s: -s.depth):
            if s.depth > 0.5:
                s.draw(painter, a_at(s.x), tint, ps)
        # 小魚の魚群（合流・分裂しながら回遊。奥の層とスノーの間）
        if self.schools:
            self.schools.draw(painter, a_at, tint, ps)
        # マリンスノー（奥のオブジェクトと手前のオブジェクトの間）
        for f in self.snow:
            f.draw(painter, ground_y - 2 * ps)
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
