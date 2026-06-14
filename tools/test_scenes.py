# -*- coding: utf-8 -*-
"""シーンプラグインの回帰テスト（新モード追加時にも実行する）。
1) 全シーン: 登録・タブ構築・タブ切替・gather・rebuild/update/draw（オフスクリーン）
2) 言語切替後のラベル解決
3) プリセット保存キーが gather の出力に存在すること
private_scenes/ にあるモードも自動的にテスト対象になる。
usage: python tools/test_scenes.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QPixmap

app = QApplication(sys.argv)

import main
from scenes import (scene_registry, get_scene_class, get_scale_key,
                    get_preset_keys, SCENE_MODES)
from i18n import t, set_language

failures = []


def check(cond, msg):
    if cond:
        print("  ok:", msg)
    else:
        failures.append(msg)
        print("  NG:", msg)


print("== registered scenes ==")
keys = [i["key"] for i in scene_registry()]
print(" ", keys)
check(keys[:7] == ["grass", "aquarium", "tokaido", "pooh", "takibi",
                   "skating", "shark"],
      "public modes keep the legacy fixed order")

print("== labels resolve in both languages ==")
for lang in ("ja", "en"):
    set_language(lang)
    for k, label_key in SCENE_MODES:
        label = t(label_key)
        check(label != label_key, f"{lang}:{label_key} -> {label}")
set_language("ja")

print("== dialog build / tab switching / gather ==")
dlg = main.SettingsDialog(
    config={"scene_mode": "grass"},
    on_apply=lambda cfg: None,
    on_save=lambda c, d: None,
    on_load=lambda c, n: None,
)
cfg = dlg._gather_config()
for k, _ in SCENE_MODES:
    dlg._update_tabs_for_scene(k)
    n_tabs = len(dlg._scene_tabs.get(k, []))
    check(n_tabs >= 1, f"{k}: has {n_tabs} settings tab(s)")
    # シーン設定ページの内側タブが当該シーンの設定になっている
    check(dlg._scene_inner.count() == n_tabs,
          f"{k}: scene-settings inner tab count = {dlg._scene_inner.count()}")
    if n_tabs:
        first = dlg._scene_inner.widget(0)
        check(any(first is w for w, _ in dlg._scene_tabs[k]),
              f"{k}: scene tab shown in scene-settings page")
    # preset_keys は gather 出力（+seed）に含まれる
    missing = [p for p in get_preset_keys(k)
               if p != "seed" and p not in cfg]
    check(not missing, f"{k}: preset keys all in gather output {missing}")
    check(isinstance(get_scale_key(k), str) and get_scale_key(k).endswith("scale"),
          f"{k}: scale_key = {get_scale_key(k)}")

print("== scene rebuild/update/draw (offscreen) ==")
for k, _ in SCENE_MODES:
    cls = get_scene_class(k)
    scene = cls()
    conf = dict(cfg)
    conf["scene_mode"] = k
    conf["seed"] = 42
    h = scene.get_area_height(conf)
    scene.rebuild(conf, 1920, 1920)
    wind = main.WindSimulator()
    for _ in range(30):
        wind.update(1 / 60.0)
        scene.update(wind, mouse_pos=(400, 50))
    pix = QPixmap(1920, h)
    pix.fill()
    p = QPainter(pix)
    if scene.has_background_layer():
        scene.draw_background(p, h, None, None)
    scene.draw(p, h, None, None)
    p.end()
    check(True, f"{k}: rebuild+update+draw (h={h})")

print("== language switch rebuilds dialog texts ==")
set_language("en")
dlg2 = main.SettingsDialog(
    config={"scene_mode": "shark"},
    on_apply=lambda cfg: None,
    on_save=lambda c, d: None,
    on_load=lambda c, n: None,
)
check(dlg2._scene_inner.tabText(0) == "Deep Sea Settings",
      f"en shark tab label = {dlg2._scene_inner.tabText(0)}")
set_language("ja")

print()
if failures:
    print("FAILED:", len(failures))
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("ALL PASS")
