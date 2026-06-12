# 1/f モードプラグイン制作ガイド

1/f の「モード」（草原・焚火・深海のサメ…）は、**Python ファイル1つで作れるプラグイン**です。
このガイドは、自分のモードを作って配布（将来は **liplico store**＝LINEスタンプの
クリエイターズマーケットのような場で販売）するまでの全てを説明します。

- 雛形: [`plugins/_template.py`](../plugins/_template.py)（風に揺れるチューリップ。動く見本）
- 検証: `python tools/validate_plugin.py あなたのモード.py`

## パッケージとは

**1ファイル = 1モード = 1パッケージ**。`.py` ファイルそのものが配布物です。
ドット絵はコードで描く文化なので（既存モードも全てそう）、画像等の同梱は不要です。

ユーザーのインストール方法は「プラグインフォルダに置くだけ」:

| OS | プラグインフォルダ |
|---|---|
| Windows | `%APPDATA%\1f\plugins\` |
| macOS | `~/Library/Application Support/1f/plugins/` |

次回起動時にモード一覧へ自動で追加されます。アンインストールはファイル削除。

> **liplico store（仮称・準備中）**: 将来はストアで販売・購入後ダウンロードという
> LINEスタンプ型の流通になります。DRM はかけない方針のため、ストア配布物も
> この同じ `.py` パッケージです。`SCENE["meta"]` がストア掲載情報になります。

## クイックスタート（5分）

1. このリポジトリを clone して依存を入れる:
   ```
   git clone https://github.com/me-keh-dev/1f.git
   cd 1f
   pip install -r requirements.txt
   ```
2. 雛形をコピー: `plugins/_template.py` → `plugins/mymode.py`
   （`_` で始まるファイル名は読み込まれないので必ずリネーム）
3. `python main.py` で起動 → トレイの設定 → モード一覧に「チューリップ」が出る
4. コードを書き換えながら再起動して育てる
5. 検証: `python tools/validate_plugin.py plugins/mymode.py` が PASS になればOK

## SCENE 契約リファレンス

モジュール末尾に `SCENE` 辞書を定義します。エンジンはこの辞書だけを見ます。

| フィールド | 必須 | 説明 |
|---|---|---|
| `key` | ✔ | モードの内部名。英小文字・全モードで一意（例 `"tulip"`）。config キーの接頭辞にも使う |
| `label_key` | ✔ | モード一覧に出す名前の i18n キー。`texts` で定義する |
| `class` | ✔ | `BaseScene` のサブクラス（下記） |
| `order` |  | 一覧の表示順。**配布プラグインは 200 以上**（〜70 は同梱モード、100〜199 は公式追加分） |
| `scale_key` |  | 表示倍率の config キー。画面左下メニューボタンのサイズ連動に使われる |
| `preset_keys` |  | 「シーンを保存」で保存される config キーのリスト（`"seed"` を含めるのが普通） |
| `preset_label_key` |  | プリセット枠のタイトル i18n キー（省略時は汎用ラベル） |
| `texts` |  | `{"ja": {...}, "en": {...}}`。このモード専用ラベル。エンジン既存キーは上書き不可 |
| `build_settings` |  | `fn(dialog) -> [(QWidget, タブ名), ...]`。設定タブを作る |
| `gather` |  | `fn(dialog) -> dict`。設定タブの現在値を config 辞書で返す |
| `meta` |  | ストア掲載用: `author` / `version` / `description` / `license`。**ストア提出時に必須** |

### config キーの命名規則

モード独自の設定キーは **`<key>_` を接頭辞**にしてください（例 `tulip_count`）。
全モードの設定は1つの config 辞書に同居するため、衝突すると他のモードを壊します。
`validate_plugin.py` が衝突を検査します。

## BaseScene リファレンス（`scenes/base.py`）

実装するメソッド:

```python
class MyScene(BaseScene):
    def get_area_height(self, config) -> int:
        """タスクバー上に確保する高さ(px)。表示倍率に連動させる"""

    def rebuild(self, config, screen_width, widget_width):
        """起動時・設定変更・再生成で呼ばれる。config["seed"] で再現可能にする"""

    def update(self, wind_sim, mouse_pos=None):
        """毎フレーム（約90fps）。重い処理は数フレームに1回に間引く"""

    def draw(self, painter, ground_y, tint=None, get_alpha=None):
        """QPainter で描画。ground_y が地面のY座標"""

    # 任意: ウィンドウの後ろに回り込む背景レイヤー（遠景の山・海底地形など）
    def has_background_layer(self) -> bool: ...
    def draw_background(self, painter, ground_y, tint=None, get_alpha=None): ...
```

### 守ってほしいお約束

1. **tint を全ドットに適用** — 時間帯ライティング（朝焼け・夜）の色補正。
   `from scenes.base import apply_tint` → `apply_tint(QColor(...), tint)`
2. **get_alpha を全ドットに適用** — マウス近接フェード。
   `alpha = get_alpha(base_x) if get_alpha else 255`
3. **画面左下を避ける** — メニューボタンのエリア。
   `from scenes.base import hamburger_avoid_px` → rebuild で `x >= hamburger_avoid_px(scale)`
4. **seed で再現可能に** — `random.Random(config.get("seed", 0))` を使う。
   「再生成」ボタンは seed を変えて rebuild を呼び直す仕組み
5. **ドットの単位** — `from scenes.base import PIXEL_SIZE`（=4）×表示倍率を1ドットとして
   `painter.fillRect(x, y, ps, ps, color)` で打つ
6. **例外を出さない** — 描画中の未捕捉例外はログに記録される。設定値の端
   （スライダー最小・最大）でも落ちないこと

### 使える環境情報

- **風（1/fゆらぎ）**: `wind_sim.get_wave_at(x)` が位置 x の風の強さ（-2〜+2程度の波）。
  草・炎・水草はすべてこれで揺れている。`wind_sim.time` は経過時間
- **サウンド連動**: `wind_sim.sound_level`（音量 0..2）、`wind_sim.sound_bass`
  （キックの「ドン!」パルス 0..2）。get_wave_at には自動で加算済み
- **天気**: `self.is_raining`（雨か）と `self.weather_state`（"clear"/"rain"/"snow"等）。
  東海道の旅人はこれで傘をさす
- **時刻**: `datetime.datetime.now()` で独自の時間帯演出も可（焚火の深夜消灯など）

## 設定タブの作り方

`build_settings(dialog)` の中で部品を組み立てます:

```python
def _build_settings(dialog):
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QCheckBox
    from i18n import t
    tab = QWidget()
    layout = QVBoxLayout(tab)
    # スライダー（変更すると自動で gather → rebuild される）
    dialog.mymode_count_slider = dialog._add_slider(
        layout, t("mymode_count"), 1, 50, dialog.config.get("mymode_count", 10))
    # チェックボックスは toggled を dialog._on_slider_changed につなぐ
    cb = QCheckBox(t("mymode_lights"))
    cb.setChecked(dialog.config.get("mymode_lights", True))
    cb.toggled.connect(dialog._on_slider_changed)
    dialog.mymode_lights_check = cb
    layout.addWidget(cb)
    layout.addStretch()
    return [(tab, t("mymode_settings"))]
```

- ウィジェットは `dialog.<key>_xxx` 属性に保存し、`gather(dialog)` で読み返す
- 項目が多いときは `QScrollArea` で包む（skating タブが見本）
- タブを2枚以上返してもよい（grass が「草」「配置」の2枚）

## 安定API（互換性の約束）

以下はエンジン更新で壊さないことを約束する境界です:

- `SCENE` 契約の全フィールド
- `BaseScene` のメソッドシグネチャと `weather_state` / `is_raining`
- `scenes.base`: `PIXEL_SIZE` / `apply_tint` / `hamburger_avoid_px` / `PinkNoiseGenerator`
- `wind_sim`: `get_wave_at(x)` / `time` / `sound_level` / `sound_bass`
- `dialog`: `config` / `_add_slider(...)` / `_on_slider_changed`
- `i18n.t(key)`

これ以外（main.py の内部等）に依存すると更新で壊れることがあります。

## 検証とテスト

```
python tools/validate_plugin.py plugins/mymode.py   # 契約チェック（提出前に必須）
python tools/test_scenes.py                          # 全モードの回帰テスト
python main.py                                       # 実機確認
```

`validate_plugin.py` は契約・ラベル・キー衝突・オフスクリーン描画・ストア用 meta を
まとめて検査します。**PASS にならないものはストアに提出できません。**

## 配布

- **今すぐ**: `.py` ファイルをそのまま配布 → 受け取った人がプラグインフォルダに置く
- **将来（liplico store）**: ストアに提出 → 審査 → 販売。購入者はストアから
  ダウンロードしてプラグインフォルダへ（または自動インストール）。
  `meta` の `author` / `version` / `description` / `license` が掲載情報になります

### 注意事項

- プラグインは**普通の Python コード**として実行されます。利用者は信頼できる
  配布元（ストア・作者公式）からのみ入手してください
- 他者の著作物（既存ゲーム・アニメのキャラ等）を模したモードは配布できません。
  パブリックドメイン作品は出典明記の上で可（同梱の「風船プーさん」が前例）
- エンジン（1/f 本体）は MIT ライセンスです。あなたのプラグインのライセンスは
  あなたが決められます（`meta.license` に明記）
