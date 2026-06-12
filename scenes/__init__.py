"""Scene registry - 起動時に scenes/（OSS）と private_scenes/（非公開）を
スキャンしてシーンプラグインを自動登録する。

プラグイン契約: シーンモジュールはモジュール末尾に SCENE 辞書を定義する。
  SCENE = {
      "key": "takibi",              # config の scene_mode 値（一意）
      "label_key": "scene_takibi",  # モード名の i18n キー
      "class": TakibiScene,          # BaseScene のサブクラス
      "order": 50,                   # モード一覧の表示順（公開 10..70 / 非公開 100+）
      "scale_key": "takibi_scale",  # 表示倍率の config キー（ハンバーガー連動）
      "preset_keys": [...],          # 「シーンを保存」で保存する config キー
      "preset_label_key": "...",    # （任意）プリセット枠タイトルの i18n キー
      "texts": {"ja": {...}, "en": {...}},   # シーン専用の i18n ラベル
      "build_settings": fn(dialog) -> [(QWidget, タブ名), ...],  # 設定タブ
      "gather": fn(dialog) -> dict,  # 設定タブから config を読む
  }

新モードの追加は scenes/ か private_scenes/ に .py を1つ置くだけで、
エンジン側（main.py / i18n.py / このファイル）の変更は不要。
"_" で始まるモジュール名と base.py はスキャン対象外。
壊れたモジュールが1つあっても他のモードは起動する（読み込み失敗は黙殺・記録のみ）。
"""
import importlib
import os
import sys
import traceback

from i18n import register_texts

DEFAULT_SCENE = "grass"

# 旧来の固定順を維持するための表示順（SCENE["order"]）
# grass=10, aquarium=20, tokaido=30, pooh=40, takibi=50, skating=60, shark=70

_REGISTRY = {}   # key -> SCENE辞書（"module"を追記）


def _register_package(pkg_name):
    """パッケージ内の *.py をインポートして SCENE 辞書を登録する"""
    try:
        pkg = importlib.import_module(pkg_name)
    except ImportError:
        return  # private_scenes が無い構成（OSSのみ）は正常
    pkg_dir = os.path.dirname(os.path.abspath(pkg.__file__))
    try:
        names = sorted(os.listdir(pkg_dir))
    except OSError:
        return
    for fn in names:
        if not fn.endswith(".py"):
            continue
        name = fn[:-3]
        if name.startswith("_") or name == "base":
            continue
        try:
            mod = importlib.import_module(pkg_name + "." + name)
        except Exception:
            # 1モジュールの不具合で全体を道連れにしない（配信更新の安全弁）
            print("[scenes] failed to load {}.{}:".format(pkg_name, name),
                  file=sys.stderr)
            traceback.print_exc()
            continue
        info = getattr(mod, "SCENE", None)
        if not isinstance(info, dict) or "key" not in info or "class" not in info:
            continue
        info = dict(info)
        info["module"] = mod.__name__
        _REGISTRY[info["key"]] = info
        if info.get("texts"):
            register_texts(info["texts"])


def _scan():
    _REGISTRY.clear()
    _register_package(__name__)        # scenes/（OSS同梱モード）
    _register_package("private_scenes")  # 非公開モード（存在すれば）


_scan()


def scene_registry():
    """登録済みシーンの SCENE 辞書を表示順で返す"""
    return sorted(_REGISTRY.values(),
                  key=lambda i: (i.get("order", 999), i["key"]))


def get_scene_info(scene_mode):
    """SCENE 辞書を返す（未知のモードはデフォルトの草原）"""
    return _REGISTRY.get(scene_mode) or _REGISTRY[DEFAULT_SCENE]


def get_scene_class(scene_mode):
    return get_scene_info(scene_mode)["class"]


def get_scale_key(scene_mode):
    """シーンの表示倍率 config キー（ハンバーガーボタンのサイズ連動用）"""
    return get_scene_info(scene_mode).get("scale_key", "grass_scale")


def get_preset_keys(scene_mode):
    """「シーンを保存」で保存する config キー"""
    return list(get_scene_info(scene_mode).get("preset_keys", ()))


# 後方互換: [(キー, ラベルのi18nキー), ...] を表示順で
SCENE_MODES = [(i["key"], i["label_key"]) for i in scene_registry()]
