# -*- coding: utf-8 -*-
"""モードプラグインの検証ツール（クリエイター向け / liplico store 提出前チェック）。

usage: python tools/validate_plugin.py <your_mode.py> [--preview out.png]

チェック内容:
  1. SCENE 契約の必須フィールドと型
  2. ラベルが日英両方で解決できること
  3. 設定タブが構築でき、gather が dict を返すこと
  4. preset_keys / scale_key が gather の出力（+seed）に含まれること
  5. config キーが既存モードと衝突しないこと
  6. rebuild / update / draw がオフスクリーンで例外なく動くこと
  7. ストア用 meta（author / version / description / license）の有無（警告のみ）

--preview out.png を付けると描画結果（昼・夜ティント・少し時間が進んだ3コマ）を
1枚のPNGに並べて保存する。AIコーディング環境（Claude Code / Codex 等）で
開発するときは、これをエージェントに読ませて見た目を確認・反復させるとよい。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print("  NG:", msg)


def ok(msg):
    print("  ok:", msg)


def warn(msg):
    warnings.append(msg)
    print("  !! :", msg)


def main():
    args = sys.argv[1:]
    preview_path = None
    if "--preview" in args:
        i = args.index("--preview")
        preview_path = args[i + 1] if i + 1 < len(args) else "preview.png"
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(2)
    path = os.path.abspath(args[0])
    if not os.path.isfile(path):
        print("file not found:", path)
        sys.exit(2)
    if os.path.basename(path).startswith("_"):
        warn('ファイル名が "_" で始まるとアプリに読み込まれません'
             '（雛形のままなら配布前にリネーム）')

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QPainter, QPixmap
    app = QApplication(sys.argv[:1])  # noqa: F841

    import main as app_main
    import scenes
    from i18n import t, set_language

    print("== 1. SCENE 契約 ==")
    builtin_keys = {i["key"] for i in scenes.scene_registry()}
    try:
        info = scenes.register_plugin_file(path)
    except ValueError as e:
        err(str(e))
        if "already exists" in str(e):
            err("key が既存モードと衝突しています。別の名前にしてください")
        _finish()
        return
    key = info["key"]
    ok(f"loaded: key={key!r}")
    if not isinstance(key, str) or not key or not key.islower():
        err("key は空でない英小文字の文字列にしてください")
    if not isinstance(info.get("order", 999), int):
        err("order は整数にしてください")
    elif info.get("order", 999) < 100:
        warn("order は 100 未満が同梱モード用です。配布プラグインは 200+ 推奨")
    for f in ("build_settings", "gather"):
        if not callable(info.get(f)):
            err(f"{f} が callable ではありません（設定タブが出せません）")

    print("== 2. ラベル（日英） ==")
    for lang in ("ja", "en"):
        set_language(lang)
        label = t(info["label_key"])
        if label == info["label_key"]:
            err(f"{lang}: label_key={info['label_key']!r} が texts にありません")
        else:
            ok(f"{lang}: {label}")
    set_language("ja")

    print("== 3. 設定タブと gather ==")
    dlg = app_main.SettingsDialog(
        config={"scene_mode": key},
        on_apply=lambda c: None,
        on_save=lambda c, d: None,
        on_load=lambda c, n: None,
    )
    tabs = dlg._scene_tabs.get(key) or []
    if not tabs:
        err("設定タブが構築されませんでした（build_settings を確認）")
    else:
        ok(f"設定タブ {len(tabs)} 枚: {[lbl for _, lbl in tabs]}")
    try:
        gathered = info["gather"](dlg) if callable(info.get("gather")) else {}
    except Exception as e:
        gathered = {}
        err(f"gather が例外: {e!r}")
    if not isinstance(gathered, dict):
        err("gather は dict を返してください")
        gathered = {}
    else:
        ok(f"gather keys: {sorted(gathered)}")

    print("== 4. preset_keys / scale_key ==")
    missing = [p for p in info.get("preset_keys", ())
               if p != "seed" and p not in gathered]
    if missing:
        err(f"preset_keys が gather の出力にありません: {missing}")
    else:
        ok("preset_keys は gather と整合")
    sk = info.get("scale_key")
    if not sk:
        warn("scale_key がありません（メニューボタンのサイズ連動が効きません）")
    elif sk not in gathered:
        err(f"scale_key={sk!r} が gather の出力にありません")
    else:
        ok(f"scale_key: {sk}")

    print("== 5. config キーの衝突 ==")
    base_cfg = dlg._gather_config()
    others = {}
    for other in scenes.scene_registry():
        if other["key"] in (key,):
            continue
        g = other.get("gather")
        if callable(g):
            try:
                for ck in g(dlg):
                    others[ck] = other["key"]
            except Exception:
                pass
    clashes = {ck: others[ck] for ck in gathered if ck in others}
    if clashes:
        err(f"config キーが他モードと衝突: {clashes}（接頭辞を付けてください）")
    else:
        ok("config キーの衝突なし")

    print("== 6. rebuild / update / draw（オフスクリーン） ==")
    try:
        from PyQt5.QtGui import QColor
        scene = info["class"]()
        conf = dict(base_cfg)
        conf.update(gathered)
        conf["seed"] = 42
        h = scene.get_area_height(conf)
        if not isinstance(h, int) or h <= 0:
            err(f"get_area_height は正の int を返してください（{h!r}）")
        scene.rebuild(conf, 1920, 1920)
        wind = app_main.WindSimulator()

        def render(tint, get_alpha, w=960):
            pix = QPixmap(w, max(h, 1))
            pix.fill(QColor(16, 18, 24))  # 暗背景＝デスクトップ想定
            p = QPainter(pix)
            if scene.has_background_layer():
                scene.draw_background(p, h, tint, get_alpha)
            scene.draw(p, h, tint, get_alpha)
            p.end()
            return pix

        frames = []
        for _ in range(60):           # 1秒ぶん動かす
            wind.update(1 / 60.0)
            scene.update(wind, mouse_pos=(400, 50))
        frames.append(render(None, None))                       # 昼
        for _ in range(120):          # さらに2秒（動きの差が見える）
            wind.update(1 / 60.0)
            scene.update(wind, mouse_pos=(400, 50))
        frames.append(render(None, lambda x: 200))              # フェードあり
        frames.append(render((0.30, 0.32, 0.55), None))         # 夜ティント
        ok(f"描画OK（高さ {h}px）")

        if preview_path:
            sheet = QPixmap(960, (max(h, 1) + 4) * len(frames))
            sheet.fill(QColor(40, 40, 40))
            p = QPainter(sheet)
            for i, f in enumerate(frames):
                p.drawPixmap(0, i * (max(h, 1) + 4), f)
            p.end()
            sheet.save(preview_path)
            ok(f"プレビュー保存: {preview_path}"
               "（上=昼 / 中=マウスフェード / 下=夜ライティング）")
    except Exception as e:
        import traceback
        traceback.print_exc()
        err(f"シーン実行で例外: {e!r}")

    print("== 7. ストア用 meta（liplico store 提出時に必要） ==")
    meta = info.get("meta") or {}
    for f in ("author", "version", "description", "license"):
        if meta.get(f):
            ok(f"meta.{f}: {meta[f]}")
        else:
            warn(f"meta.{f} がありません（ストア提出時に必要になります）")

    _finish()


def _finish():
    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        sys.exit(1)
    if warnings:
        print(f"PASS（警告 {len(warnings)} 件）")
    else:
        print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
