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
import datetime
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
    return _register_scene_obj(mod, mod_name, where=path, overwrite=overwrite)


def _register_scene_obj(mod, module_name, where, overwrite=False, extra=None):
    """モジュールオブジェクトの SCENE を検証して _REGISTRY に登録する共通処理"""
    info = getattr(mod, "SCENE", None)
    if not isinstance(info, dict):
        raise ValueError("SCENE dict not found in " + where)
    missing = [f for f in ("key", "label_key", "class") if f not in info]
    if missing:
        raise ValueError("SCENE is missing {} in {}".format(missing, where))
    info = dict(info)
    info["module"] = module_name
    if extra:
        info.update(extra)
    if info["key"] in _REGISTRY and not overwrite:
        raise ValueError("scene key {!r} already exists (skipped {})"
                         .format(info["key"], where))
    _REGISTRY[info["key"]] = info
    if info.get("texts"):
        register_texts(info["texts"])
    return info


def register_plugin_source(source, name, where, overwrite=False, extra=None):
    """ファイルではなくソース文字列（.1fmode の zip 内 mode.py など）から登録する。
    署名付きコラボシーンのローダーが使う。"""
    import types
    mod_name = "onef_collab_" + name
    mod = types.ModuleType(mod_name)
    mod.__dict__["__file__"] = where
    try:
        exec(compile(source, "<collab:%s>" % name, "exec"), mod.__dict__)
    except Exception as e:
        raise ValueError("failed to exec {}: {!r}".format(where, e))
    sys.modules[mod_name] = mod
    return _register_scene_obj(mod, mod_name, where, overwrite=overwrite,
                               extra=extra)


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


# 直近のスキャンで期限切れ削除されたコラボシーンの表示名（main が通知に使う）
_last_expired = []


def _register_installed_collabs():
    """installed/ の署名付きコラボシーン（.1fmode）を検証して登録。
    期限切れは自動削除し、その表示名を _last_expired に積む（通知用）。"""
    from scenes import _collab
    try:
        entries, expired = _collab.scan_installed()
    except Exception:
        # コラボ機構の不具合で同梱モードを道連れにしない
        traceback.print_exc()
        return
    _last_expired.extend(expired)
    for manifest, src, expiry in entries:
        key = manifest.get("key", "?")
        try:
            # コラボは同梱モードを乗っ取れない（overwrite=False）。
            # 終了日を SCENE.available にも反映して一覧ラベル/期限判定を共通化
            extra = {}
            av = manifest.get("available")
            if av:
                extra["available"] = av
            register_plugin_source(src, key, where="<collab:%s>" % key,
                                   overwrite=False, extra=extra)
        except ValueError as e:
            print("[scenes] collab skipped:", e, file=sys.stderr)


def _scan():
    _REGISTRY.clear()
    del _last_expired[:]
    _register_package(__name__)        # scenes/（OSS同梱モード）
    _register_package("private_scenes")  # 非公開モード（存在すれば）
    for d in _plugin_dirs():           # ユーザープラグイン（最後＝同梱優先）
        _register_plugin_dir(d)
    _register_installed_collabs()      # 署名付きコラボ（一般ユーザー向け）


def rescan():
    """日付変更・新規インストール後にモード一覧を作り直し、
    今回新たに期限切れ削除されたコラボの表示名を返す。"""
    _scan()
    return consume_expired()


def register_trial(key, source):
    """お試し用にシーンを一時登録する（保存しない・上書き可）。
    end_trial 相当で unregister すること。"""
    return register_plugin_source(source, key, where="<trial:%s>" % key,
                                  overwrite=True)


def unregister(key):
    """一時登録したシーンを取り除く（お試し終了時）"""
    info = _REGISTRY.pop(key, None)
    if info:
        sys.modules.pop(info.get("module", ""), None)


def consume_expired():
    """前回スキャン以降に期限切れ削除されたコラボの表示名を返してクリアする"""
    names = list(_last_expired)
    _last_expired.clear()
    return names


_scan()


# --- 期間限定モード（コラボ用） -------------------------------------------
# SCENE に "available": {"from": "2026-07-01", "until": "2026-07-31"} を
# 持たせると、その期間だけモード一覧に出る（両端とも当日を含む・ローカル日付）。
# 事前に配信しておけば開始日に全ユーザーで自動出現し、終了日の翌日に自動消滅する。
# 期限切れモードを使用中の場合は get_scene_info がデフォルトへフォールバックし、
# main.py 側の定期チェックが config を実際に切り替える。

def _parse_date(s):
    return datetime.date(*[int(x) for x in str(s).split("-")])


def is_scene_available(info, today=None):
    """期間限定モードが今日有効か（available が無ければ常に有効）"""
    av = info.get("available")
    if not av:
        return True
    today = today or datetime.date.today()
    try:
        if av.get("from") and today < _parse_date(av["from"]):
            return False
        if av.get("until") and today > _parse_date(av["until"]):
            return False
    except (ValueError, TypeError):
        return False  # 日付が壊れているモードは出さない
    return True


def scene_registry(include_unavailable=False):
    """登録済みシーンの SCENE 辞書を表示順で返す（期間外のモードは除く）"""
    infos = sorted(_REGISTRY.values(),
                   key=lambda i: (i.get("order", 999), i["key"]))
    if include_unavailable:
        return infos
    return [i for i in infos if is_scene_available(i)]


def scene_modes():
    """[(キー, ラベルのi18nキー), ...] を現時点の有効モードで返す。
    期間限定モードの自動出現/消滅に追従するため、UI構築時は
    モジュール定数 SCENE_MODES ではなくこちらを呼ぶ"""
    return [(i["key"], i["label_key"]) for i in scene_registry()]


def get_scene_info(scene_mode):
    """SCENE 辞書を返す（未知・期間外のモードはデフォルトの草原）"""
    info = _REGISTRY.get(scene_mode)
    if info is None or not is_scene_available(info):
        return _REGISTRY[DEFAULT_SCENE]
    return info


def get_scene_class(scene_mode):
    return get_scene_info(scene_mode)["class"]


def get_scale_key(scene_mode):
    """シーンの表示倍率 config キー（ハンバーガーボタンのサイズ連動用）"""
    return get_scene_info(scene_mode).get("scale_key", "grass_scale")


def get_preset_keys(scene_mode):
    """「シーンを保存」で保存する config キー"""
    return list(get_scene_info(scene_mode).get("preset_keys", ()))


def limited_until(scene_mode):
    """期間限定モードの終了日（datetime.date）。無期限なら None。
    モード一覧に「〜7/31」等を添えるのに使う"""
    info = _REGISTRY.get(scene_mode) or {}
    av = info.get("available") or {}
    if not av.get("until"):
        return None
    try:
        return _parse_date(av["until"])
    except (ValueError, TypeError):
        return None


# 後方互換: 起動時点の有効モードのスナップショット。
# 期間限定モードに追従する箇所（設定画面・起動抽選・定期チェック）は
# scene_modes() / scene_registry() を都度呼ぶこと
SCENE_MODES = scene_modes()
