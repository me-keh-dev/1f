# 窓モード（ペンディング中）

YouTube定点カメラを窓越しに表示するシーンモード。一旦ペンディングとしてソースコードから隔離。

## 内容
- `window.py` — シーン本体（元の場所: `scenes/window.py`）
- `window_mode.patch` — main.py / i18n.py / scenes/__init__.py / platform_win.py / 1f.spec への変更差分

## 復元方法
```bash
cp pending/window/window.py scenes/window.py
git apply pending/window/window_mode.patch
```
注意: patch には 1f.spec の `scenes.pooh` 追加も含まれるが、これは既に本体に適用済みのため、適用時にコンフリクトしたら 1f.spec のみ手動で `'scenes.window', 'PyQt5.QtWebEngineWidgets'` を hiddenimports に追加する。
