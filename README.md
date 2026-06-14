# 1/f

**タスクバー（Windows）/ Dock（macOS）の上にドット絵の草を生やし、1/fゆらぎの風で揺らす実験的なデスクトップ環境オーバーレイ**

[English](#english) | [日本語](#日本語)

---

## 日本語

### これは何？

タスクバーのすぐ上にファミコン風のドット絵の草が生え、1/fゆらぎで自然に揺れます。風が左から右に波のように伝播し、まるで高原の草原のような動きを作り出します。天気に連動して雨や雪が降り、時間帯で草の色が変わります。

**デスクトップオーバーレイ『1/f』は、静かすぎると集中しづらい・適度な環境の動きがあるほうが落ち着く——そんな傾向のある人のための、実験的な視覚環境ツールです。** 着想はADHDのノイズ研究（後述）から得ていますが、本アプリ自体に集中支援の効果があるかは、**まだ誰も検証していない未検証の仮説**です。

> 製品名の『1/f』は、揺れの性質である「1/fゆらぎ」にちなんでいます。本書では、固有名詞（製品）を指すときは **『1/f』**、揺れの現象を指すときは **「1/fゆらぎ」** と書き分けます。

**2つのモードで使えます：**

- **フォーカスモード** — 作業中の画面の隅に、**能動的な関与を求めず受動的に眺められる視覚的ゆらぎ**（揺れる草のような抽象的なものや、水槽のような穏やかなテーマ）を添えるモード。「静かすぎる環境より集中しやすいのでは」という仮説に基づく実験的な使い方です（効果は未検証）。
- **デコレーションモード** — 静かな草原の景色を楽しむデスクトップ装飾。風を穏やかにし、天気やライティングで季節感のある環境を作ります。

### 背景：このアプリの着想

**静かすぎる環境では覚醒レベルが下がり、集中を維持しにくくなる**——その度合いは人によって連続的に異なります（はっきり二分できるものではありません）。この傾向は、主にADHD傾向のある人を対象とした**聴覚**の研究で報告されてきました。一方で、動画や音楽など意味のある刺激は、意識がそちらに引き込まれてしまいます。

こうした「適度な環境ノイズ」を提供するツールは**聴覚**の領域では数多く存在します（Lo-Fiミュージック、カフェの環境音、ホワイトノイズアプリなど）。しかし**視覚**の領域では、装飾ツールか、逆に刺激を制限するブロッカー系ツールが中心で、**「受動的に眺められる（能動的な関与を求めない）視覚的ゆらぎを添える」** というアプローチはほとんど見当たりませんでした。『1/f』は、その空白を**実験的に**埋めてみる試みです。

### 科学的背景：確立していることと、未検証のこと

本アプリの着想元と、その限界を正直に分けて記します。効果は否定も肯定もせず、**まだ検証されていないオープンな問い**として扱います。

#### 確立していること（聴覚ノイズ）

適度な**聴覚**ノイズが、ADHD傾向のある人の認知課題成績を改善しうることは、複数の研究で報告されています。これは**確率共鳴（Stochastic Resonance）**／**中程度脳覚醒（Moderate Brain Arousal）モデル** といった枠組みで説明される、という仮説が提唱されています。

- Söderlund, Sikström & Smart (2007) は、ホワイトノイズがADHD児の認知課題成績を**向上**させる一方、定型発達児では**低下**させたと報告しました（[Journal of Child Psychology and Psychiatry, 48(8), 840-847](https://acamh.onlinelibrary.wiley.com/doi/abs/10.1111/j.1469-7610.2007.01749.x)）。
- Nigg et al. (2024) の系統的レビュー／メタ分析（計335名）は、ホワイト/ピンクノイズがADHD傾向のある児童・若年成人の課題成績に統計的に有意な改善をもたらしうると報告しています（[Journal of the American Academy of Child & Adolescent Psychiatry](https://www.jaacap.org/article/S0890-8567(24)00074-1/abstract)）。

**これらはいずれも「聴覚」刺激の研究です。**

#### 本アプリの未検証の仮説（視覚）

上記の知見が**視覚**刺激に、まして本アプリの**1/fゆらぎで揺れる草**に当てはまるかは、**まだ検証されていません**。視覚刺激については臨床試験も進行中です（ClinicalTrials.gov [NCT06057441](https://clinicaltrials.gov/study/NCT06057441)）。ただし視覚的ホワイトノイズは既に検証されており、ある指標（眼球運動制御）では効果が見られなかったとの報告もあるため、「視覚は未開拓」とは言えません。本アプリが未検証なのは、それとは**別種の刺激（時間的な1/fゆらぎ）** を**別の指標（持続的注意・落ち着き）** に用いる点です。Rijmen et al. (2026) は、ランダムノイズだけでなく構造化された刺激（純音）でも神経ノイズの指標が変化しうることを示した**関連研究**ですが、これは聴覚の研究であり、**本アプリの効果を直接示す証拠ではありません**（[Journal of Attention Disorders](https://journals.sagepub.com/doi/10.1177/10870547251357074)）。

#### 仮説の射程：「意味の有無」ではなく「能動的関与の要否」

本アプリは草のほか、水槽・キャンプ・風船などの**テーマ**も提供します。これらは意味的・表象的なコンテンツを含みます。開発者の体験的な見立てとして、集中を妨げるかどうかを分けるのは「意味の有無」よりも **「能動的な関与・目標追跡を要求するか否か」** ではないか、と考えています。

- **受動的に眺められるもの**（揺れる草のような抽象的なゆらぎ、ぼんやり眺める水槽など）は、意味を含んでいても集中を妨げにくい**かもしれない**。
- **能動的な関与を要する刺激**（集中して行うゲーム、視聴を要する動画など）は集中を妨げると考えられ、**射程外**です。

この見立てに立つと、仮説の射程は「意味の薄い抽象的な1/f運動」だけでなく **「受動的に眺められる視覚的ゆらぎ全般」** まで広がります。ただしこれは確率共鳴／MBAモデル（意味の薄い刺激を想定）とは**異なる、開発者の体験に基づく別個の未検証仮説**であり、**どのテーマについても「集中に効く」と断定・標榜するものではありません**。

> **免責**：本アプリは医療機器ではありません。ADHDの診断・治療・予防を目的としたものではなく、本アプリ自体の効果は臨床的に実証されていません。

**研究者の方へ**：視覚的なゆらぎが集中を助けうるか——そしてそれを左右するのが刺激の**意味の有無**なのか、それとも**能動的な関与を要求するか否か**なのかは、いずれも未検証のオープンな問いです。これは聴覚ノイズ研究（確率共鳴／MBAモデル）から着想を得つつ、それとは区別される作業仮説で、対象も特定の診断に限らず「静かな環境で集中しづらい傾向」を持つ人を広く想定します。共同で検証してくださる研究者（心理学・認知科学・HCI など）を歓迎します（[GitHub Issue](https://github.com/me-keh-dev/1f/issues) でご連絡ください）。

### 本アプリの手法

『1/f』は、**1/fゆらぎ（自然界に遍在するゆっくりとした不規則な変動）** によって草を揺らします。風の波が画面を左から右に伝播し、各草が個別の1/fノイズで微妙に異なる動きをすることで、**意味の薄い抽象的なゆらぎ** を作業中のデスクトップに添えます。草以外のテーマ（水槽など）は意味的なコンテンツを含みますが、いずれも**受動的に眺められる（能動的な関与を求めない）** ことを共通の狙いとしています（前述「仮説の射程」を参照）。

静かすぎると集中しにくい——かといってYouTubeを流すと引き込まれる。このアプリは、その中間を狙う**実験的な試み**です（効果は未検証）。

### 特徴

- **2つのモード**: フォーカスモード（実験的な集中環境）/ デコレーションモード（デスクトップ装飾）
- **1/fゆらぎ**: Voss-McCartney アルゴリズムによる自然な揺れ
- **風の波**: 左から右にさささ〜っと伝播する風。突風もあり
- **天気連動**: 実際の天気に基づいて雨や雪のドット絵エフェクト（3レイヤー奥行き付き）
- **時間帯ライティング**: 朝焼け → 日中 → 夕暮れ → 夜（月明かり）で草の色が変化
- **完全クリック透過**: マウス操作に一切干渉しない
- **マウス近接透過**: マウスが近づくと草がフェードアウト
- **プロシージャル生成**: 草の形状・配置を自動生成。気に入ったら保存
- **3タイプの草**: しゅっとした細い草 / 葉付き草 / 花付き草
- **8色パレット**: フォレスト、エメラルド、オータム、オーシャン、サクラ、ラベンダー、サンセット、モス
- **マルチモニター対応**: 接続された全画面に草を表示
- **詳細な設定UI**: 2段タブで全パラメータをスライダー調整
- **表示切替**: Win+Ctrl+Shift+W（Windows）/ Cmd+Ctrl+Shift+W（macOS）でON/OFF

### ダウンロード

[Releases](https://github.com/me-keh-dev/1f/releases) からダウンロードしてください。

**Windows:**
1. `1f.exe` をダウンロード
2. 好きな場所に置く（例: デスクトップ、`C:\Tools\1f\` など）
3. ダブルクリックで起動

**macOS:**
1. `1f-macos` をダウンロード（GitHub Actions経由で提供予定）
2. 好きな場所に置く
3. ターミナルで `chmod +x 1f-macos && ./1f-macos` で起動

インストール作業は不要です。ダウンロードしたファイルをそのまま開けば使えます。
設定ファイルや保存データは実行ファイルと同じフォルダに自動で作られます。

### 開発者向け（ソースから実行）

```bash
# Python 3.9以上が必要です
pip install -r requirements.txt

# macOSの場合は追加で:
# pip install pyobjc-core pyobjc-framework-Cocoa

python main.py
```


### 使い方

起動するとタスクバー（Windows）/ Dock（macOS）の上に草が生えます。

- **Win+Ctrl+Shift+W**（Windows）/ **Cmd+Ctrl+Shift+W**（macOS）: 表示/非表示の切り替え
- **設定画面**: システムトレイ / メニューバーの緑のアイコンを右クリック → 「設定」
- **再生成**: 右クリック → 「再生成」で新しい草原を生成
- **終了**: 右クリック → 「終了」

### 設定項目

| カテゴリ | 設定 | 説明 |
|---|---|---|
| 草の長さ | 最小 / 最大 | 草の高さの範囲（ピクセル単位） |
| 密集エリア | 塊の数 | クラスターが何箇所あるか |
| | 総本数 | 茂みに使う草の総数 |
| | 密集度 | 各塊の詰まり具合 |
| | 間隔 | 塊どうしの距離 |
| 散在エリア | 本数 | まばらに生える草の本数 |
| | 密度 | 散在する草の間隔 |
| 草のタイプ | 細い草 / 花 | しゅっとした草と花の比率（残りが葉付き草） |
| 風 | 風の強さ | 穏やか〜強風。突風の強さにも影響 |
| マウス透過 | ON/OFF | マウス近接時の透過機能 |
| | 中心 / 範囲 / 透過度 | 透過のパラメータ |

### スクリーンショット

![1/f Screenshot](screenshot.png)

### 動作環境

- Windows 10 / 11
- macOS 12+

### 参考文献

以下は本アプリの**着想元・参考**であり、本アプリ自体の効果を実証するものではありません（前者2件は聴覚ノイズの研究）。

- Söderlund, G., Sikström, S., & Smart, A. (2007). *Listen to the noise: Noise is beneficial for cognitive performance in ADHD.* Journal of Child Psychology and Psychiatry, 48(8), 840-847.
- Nigg, J.T., et al. (2024). *Systematic Review and Meta-Analysis: Do White Noise or Pink Noise Help With Task Performance in Youth With ADHD?* Journal of the American Academy of Child & Adolescent Psychiatry.
- Rijmen, J., Senoussi, M., & Wiersema, J.R. (2026). *Pink Noise and a Pure Tone Both Reduce 1/f Neural Noise in Adults With Elevated ADHD Traits.* Journal of Attention Disorders.
- 詳細な技術レポート（着想元として9件の論文を引用）: [docs/technical_report_ja.md](docs/technical_report_ja.md)

---

## English

### What is this?

**1/f** is an **experimental visual-environment overlay** for Windows and macOS — named after the *1/f fluctuation* it uses to animate the grass. (In this README, **1/f** refers to the product; *1/f fluctuation* refers to the sway phenomenon.)

Pixel-art grass grows above the taskbar (Windows) or Dock (macOS) and sways with 1/f fluctuation. Wind waves propagate from left to right, creating a natural meadow-like animation. Rain and snow fall based on real weather, and colors change with the time of day.

**It is built for people who tend to find it hard to focus when their surroundings are too quiet — who feel steadier with a little ambient movement** (a continuous trait, not a yes/no category). It is inspired by research on noise and ADHD (see below), but whether the app itself aids focus is an **untested hypothesis that no one has validated yet**.

**Two modes:**
- **Focus Mode** — adds **passively-viewable visual motion that doesn't demand active engagement** (abstract swaying grass, or a calm theme like an aquarium) to the edge of your working screen. Based on the hypothesis that "a little ambient visual motion might be easier to focus around than total quiet" — experimental, and its effect is unverified.
- **Decoration Mode** — Enjoy a quiet meadow scenery with gentle wind, weather effects, and time-based lighting.

### Science: what's established vs. what's untested

We separate the inspiration from its limits honestly, and treat the effect as an open, unanswered question — neither claimed nor denied.

**Established (auditory noise).** Moderate *auditory* noise has been reported to improve cognitive task performance in people with ADHD traits, described by the *stochastic resonance* / *Moderate Brain Arousal* model:

- Söderlund, Sikström & Smart (2007) reported that white noise **improved** cognitive task performance in children with ADHD while **degrading** it in typically developing children ([J Child Psychol Psychiatry, 48(8), 840-847](https://acamh.onlinelibrary.wiley.com/doi/abs/10.1111/j.1469-7610.2007.01749.x)).
- Nigg et al. (2024), a systematic review / meta-analysis (335 participants), reported a statistically significant benefit of white/pink noise on task performance in youth with ADHD traits ([JAACAP](https://www.jaacap.org/article/S0890-8567(24)00074-1/abstract)).

**These are all studies of *auditory* stimuli.**

**Untested (visual / this app).** Whether these findings extend to *visual* stimuli — let alone this app's 1/f swaying grass — **has not been tested**. A clinical trial on visual noise is ongoing (ClinicalTrials.gov [NCT06057441](https://clinicaltrials.gov/study/NCT06057441)); note, however, that visual *white* noise has already been studied and showed **no effect on one measure (oculomotor control)**, so "visual is unexplored" is not accurate. What this app leaves untested is a **different stimulus** (temporal 1/f motion) aimed at a **different outcome** (sustained attention / calmness). Rijmen et al. (2026) is *related* work but is auditory and is **not direct evidence of this app's effect** ([Journal of Attention Disorders](https://journals.sagepub.com/doi/10.1177/10870547251357074)).

#### Scope of the hypothesis: not "meaning" but "whether active engagement is required"

Beyond grass, the app offers themes such as an aquarium, a campsite, and balloons, which contain meaningful/representational content. As a developer's experiential guess, what seems to separate "distracting" from "not distracting" may be **whether a stimulus demands active engagement / goal-tracking**, rather than whether it carries meaning:

- Things you can **watch passively** (swaying grass, an aquarium you glance at) might not break focus even if they are meaningful.
- Stimuli that **demand active engagement** (a game you concentrate on, a video you have to watch) are thought to harm focus and are **out of scope**.

Under this view, the hypothesis widens from "low-meaning abstract 1/f motion" to **"passively-viewable visual motion in general."** But this is a **separate, developer-experience-based, unverified hypothesis, distinct from the stochastic-resonance / MBA model** (which assumes low-meaning stimuli), and it does **not** claim that any theme "improves focus."

> **Disclaimer:** This app is not a medical device. It is not intended to diagnose, treat, or prevent ADHD or any condition, and its effects have not been clinically validated.

**For researchers:** Whether visual fluctuation can aid focus — and whether what governs that is the **presence of meaning** or **whether the stimulus demands active engagement** — are open, untested questions. This is inspired by, but distinct from, auditory-noise research (stochastic resonance / the MBA model), and it targets not a specific diagnosis but anyone who **tends to find it hard to focus in quiet environments** (a continuous trait). We welcome researchers (psychology, cognitive science, HCI) who would like to study it together — please reach out via [GitHub Issues](https://github.com/me-keh-dev/1f/issues).

### Approach

**1/f** sways the grass with **1/f fluctuation** (the slow, irregular variation found throughout nature): a wind wave propagates left-to-right while each blade adds its own 1/f noise, placing a **low-meaning, abstract motion** at the edge of your working screen. Other themes (an aquarium and so on) do carry meaning, but the shared intent is that they can all be **watched passively, without demanding active engagement** (see "Scope of the hypothesis" above).

### Features

- **1/f noise**: Natural sway using Voss-McCartney algorithm
- **Wind waves**: Left-to-right propagating gusts with occasional strong bursts
- **Full click-through**: Zero interference with mouse input
- **Mouse proximity fade**: Grass becomes transparent near the cursor
- **Procedural generation**: Auto-generated grass shapes, save your favorites
- **3 grass types**: Slim / Leafy / Flowering
- **8 color palettes**: Forest, Emerald, Autumn, Ocean, Sakura, Lavender, Sunset, Moss
- **Detailed settings UI**: Length, density, sparseness, wind, colors, mouse fade
- **Separate save slots**: Grass presets (layout) and environment settings (wind/mouse) saved independently
- **Toggle hotkey**: Win+Ctrl+Shift+W (Windows) / Cmd+Ctrl+Shift+W (macOS)

### Download

Download from [Releases](https://github.com/me-keh-dev/1f/releases).

**Windows:** Download `1f.exe`, place it anywhere, double-click to run.

**macOS:** Download `1f-macos`, place it anywhere, run `chmod +x 1f-macos && ./1f-macos` in Terminal.

No installation required. Just open the downloaded file and it works.
Settings and save data are automatically stored in the same folder as the executable.

### For Developers (run from source)

```bash
# Requires Python 3.9+
pip install -r requirements.txt

# macOS additionally requires:
# pip install pyobjc-core pyobjc-framework-Cocoa

python main.py
```

### Usage

Grass will appear above the taskbar (Windows) / Dock (macOS) on launch.

- **Win+Ctrl+Shift+W** (Windows) / **Cmd+Ctrl+Shift+W** (macOS): Toggle visibility
- **Settings**: Right-click the tray / menu bar icon → "設定" (Settings)
- **Regenerate**: Right-click → "再生成" (Regenerate)
- **Quit**: Right-click → "終了" (Quit)

### System Requirements

- Windows 10 / 11
- macOS 12+

### Academic Background

The following are **inspiration and references** for this app, not evidence of the app's own effect (the first two concern auditory noise):

- Söderlund et al. (2007) — *Listen to the noise: Noise is beneficial for cognitive performance in ADHD*
- Nigg et al. (2024) — *Systematic Review and Meta-Analysis: Do White/Pink Noise Help With Task Performance in Youth With ADHD?*
- Rijmen et al. (2026) — *Pink Noise and a Pure Tone Both Reduce 1/f Neural Noise in Adults With Elevated ADHD Traits*

### Code Signing Policy

Windows executables are signed via [SignPath Foundation](https://signpath.org/) free code signing for OSS.

- Signing is performed exclusively through GitHub Actions CI/CD
- Only artifacts built from this repository's source code are signed
- The signing team is identical to the development team
- No functionality that compromises user privacy or security

### License

[MIT License](LICENSE)

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).
