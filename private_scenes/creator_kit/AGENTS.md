# 1/f — AIコーディングエージェント向けガイド

このリポジトリはデスクトップオーバーレイアプリ「1/f」です。あなた（Claude Code /
Codex 等のコーディングエージェント）がここで頼まれる仕事は、ほとんどの場合
**「モード（シーン）プラグインの制作」**です。

## モードプラグインを作るとき

最初に読むファイル（この順で十分です）:

1. `docs/plugin_guide.md` — SCENE 契約と使えるAPIの全リファレンス
2. `plugins/_template.py` — 動く見本（風に揺れるチューリップ）。これをコピーして始める
3. 参考実装が必要なら `scenes/` の既存モード（焚火=takibi、深海=shark が技法の見本）

### ルール

- 成果物は `plugins/<mode>.py` の **1ファイルだけ**。エンジン側
  （`main.py` / `i18n.py` / `scenes/` / spec / tools）は**変更しない**
- config キーはモード名を接頭辞にする（例 `mymode_count`）。既存モードとの
  衝突は検証ツールが検出する
- ドット絵はコードで描く（`painter.fillRect` をドット単位で）。外部画像は使わない
- `SCENE["meta"]` の author / version / description / license を必ず埋める
  （liplico store 提出時の掲載情報）

### 検証ループ（必ず回すこと）

```bash
# 1. 契約チェック＋プレビュー画像の生成
python tools/validate_plugin.py plugins/<mode>.py --preview build/preview.png

# 2. build/preview.png を自分で見る（上=昼 / 中=マウスフェード / 下=夜ライティング）
#    → 見た目が意図と違えばコードを直して 1. に戻る

# 3. 全モードの回帰テスト
python tools/test_scenes.py
```

`validate_plugin.py` が PASS し、プレビューが意図どおりになるまで反復してください。
夜ライティング（下段）で何も見えなくなるモードは tint の適用漏れか発光表現の
不足です（焚火 `scenes/takibi.py` が tint を無視して自己発光する側の見本）。

### 動作確認（GUI が使える場合）

```bash
pip install -r requirements.txt
python main.py   # トレイ常駐。設定画面のモード一覧に追加されている
```

## このリポジトリ自体の開発について

エンジン本体の開発メモ・リリース手順はメンテナ用の `CLAUDE.md` にあります。
モード制作だけならそちらを読む必要はありません。
