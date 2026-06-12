"""Scene registry - 起動時に scenes/（OSS）・private_scenes/（非公開）・
ユーザープラグインフォルダをスキャンしてシーンプラグインを自動登録する。

ユーザープラグイン:
  Windows: %APPDATA%/1f/plugins/   mac: ~/Library/Application Support/1f/plugins/
  に .py を1つ置くだけで次回起動時にモード一覧へ追加される（1ファイル=1モード）。
  検証は tools/validate_plugin.py。

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


def user_plugin_dir():
    """ユーザープラグインの置き場所（無ければ作らない。インストール先の案内用）"""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/1f")
    else:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                            "1f")
    return os.path.join(base, "plugins")


def _plugin_dirs():
    """スキャンするユーザープラグインフォルダ（存在するものだけ）"""
    dirs = [user_plugin_dir()]
    # 開発時: リポジトリ直下の plugins/（テンプレート置き場兼ローカル開発用）
    dirs.append(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "plugins"))
    return [d for d in dirs if os.path.isdir(d)]


def register_plugin_file(path, overwrite=False):
    """単一 .py のプラグインを読み込んで登録する。

    成功すれば SCENE 辞書を返す。契約違反・読み込み失敗は ValueError。
    既存モードとキーが衝突する場合は overwrite=False なら登録しない
    （同梱モードがユーザープラグインに乗っ取られないように）。
    tools/validate_plugin.py と将来のストアインストールもこれを使う。
    """
    import importlib.util
    name = os.path.splitext(os.path.basename(path))[0]
    mod_name = "onef_plugin_" + name
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    except Exception as e:
        sys.modules.pop(mod_name, None)
        raise ValueError("failed to load {}: {!r}".format(path, e))
    info = getattr(mod, "SCENE", None)
    if not isinstance(info, dict):
        raise ValueError("SCENE dict not found in " + path)
    missing = [f for f in ("key", "label_key", "class") if f not in info]
    if missing:
        raise ValueError("SCENE is missing {} in {}".format(missing, path))
    info = dict(info)
    info["module"] = mod_name
    if info["key"] in _REGISTRY and not overwrite:
        raise ValueError("scene key {!r} already exists (skipped {})"
                         .format(info["key"], path))
    _REGISTRY[info["key"]] = info
    if info.get("texts"):
        register_texts(info["texts"])
    return info


def _register_plugin_dir(dirpath):
    try:
        names = sorted(os.listdir(dirpath))
    except OSError:
        return
    for fn in names:
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        try:
            register_plugin_file(os.path.join(dirpath, fn))
        except ValueError as e:
            # 壊れた・衝突したプラグインは黙殺して他のモードで起動継続
            print("[scenes] plugin skipped:", e, file=sys.stderr)


def _scan():
    _REGISTRY.clear()
    _register_package(__name__)        # scenes/（OSS同梱モード）
    _register_package("private_scenes")  # 非公開モード（存在すれば）
    for d in _plugin_dirs():           # ユーザープラグイン（最後＝同梱優先）
        _register_plugin_dir(d)


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
