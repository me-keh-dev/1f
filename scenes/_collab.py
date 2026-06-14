"""署名付きシーン（.1fmode）の検証・自動インストール・期限自動削除。

一般ユーザーはファイルを触らない。アプリが `installed/` フォルダを管理し、
署名付きパッケージを検証して読み込み、期限が切れたら自動で削除する。
（開発者が自分で `.py` を置く `plugins/` フォルダとは別系統。）

設計: private_scenes/_design/scene_distribution.md
署名: RSA-2048 / PKCS#1 v1.5 / SHA-256。秘密鍵は private のみ、公開鍵は下に埋め込み。
検証は純標準ライブラリ（hashlib + pow）なので骨格（凍結exe）の再ビルド不要。
"""
import datetime
import hashlib
import io
import json
import os
import sys
import zipfile

# --- 埋め込み公開鍵（公開して問題ない。pubkey_id で世代管理） -----------------
# 秘密鍵は private_scenes/_keys/collab_priv.pem（非公開）。
# ローテーション時は新しい id を足し、古い id の配布を失効させる。
COLLAB_PUBKEYS = {
    1: {
        "e": 65537,
        "n": int(
            "A8A880AB1733A6F2F23A74C02658C431AB6EC6FC2168CBB0111DD4C5F001D184"
            "CD206D90DA319CEDD9D1E00817F6F17EFF52892C8082FBBD4754FD1D64C07FB8"
            "3A2275A51670C7435AA6DE568DD7536723F8C08160BC86E02715518F48F2C979"
            "FC7C1BEDC100A19C2C3B223D2589F4E6EC265902EBB4AC1D7EB0C4CC9BE09018"
            "4234067AC3A4951672599D2E2421603D3699DEADB3C5751027B1BA9A08EAEA16"
            "D69655296D1CEA724833FB64331B798672E1644CA39CF677BF9B60B564B62AEB"
            "E37400EC682A9B0FC61E6A527F3EA66E6421BE21208903706339BD6149E16617"
            "205402830DB25AA5188672F5208371AED0BC66BA913BCA297C953DCB6747B3D1",
            16),
    },
}

_ASN1_SHA256 = bytes.fromhex("3031300d060960864801650304020105000420")
MODE_FORMAT = 1

# 失効リスト（権利問題・規約違反・リコール等で配布済みシーンを後から停止する）の
# 既定取得先。version.json と同じ Cloudflare Pages。未配置(404)なら何もしない。
DEFAULT_REVOKE_URL = "https://1f-updates.pages.dev/revoked.json"

# ストアの配布カタログの既定取得先（config の store_catalog_url で上書き可）。
# 未配置(404)なら空＝ストアには所有シーンだけが並ぶ。
DEFAULT_CATALOG_URL = "https://1f-updates.pages.dev/catalog.json"


def _verify_rsa(msg, sig, pubkey):
    """RSA-PKCS#1 v1.5 / SHA-256 署名検証（純標準ライブラリ）"""
    n, e = pubkey["n"], pubkey["e"]
    k = (n.bit_length() + 7) // 8
    if len(sig) != k:
        return False
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
    t = _ASN1_SHA256 + hashlib.sha256(msg).digest()
    if len(em) < len(t) + 11:
        return False
    expected = b"\x00\x01" + b"\xff" * (k - 3 - len(t)) + b"\x00" + t
    return em == expected


class CollabError(Exception):
    pass


def _parse_date(s):
    return datetime.date(*[int(x) for x in str(s).split("-")])


def load_and_verify(path):
    """.1fmode を開いて署名・整合性を検証し (manifest, mode_source) を返す。
    検証に失敗したら CollabError を投げる（=登録しない）。"""
    try:
        with zipfile.ZipFile(path) as z:
            manifest_raw = z.read("manifest.json")
            sig = z.read("manifest.sig")
            mode_src = z.read("mode.py")
    except (zipfile.BadZipFile, KeyError, OSError) as e:
        raise CollabError("壊れたパッケージ: {!r}".format(e))

    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise CollabError("manifest が不正: {!r}".format(e))

    if manifest.get("format") != MODE_FORMAT:
        raise CollabError("未対応のフォーマット版: {}".format(manifest.get("format")))

    pubkey = COLLAB_PUBKEYS.get(manifest.get("pubkey_id"))
    if not pubkey:
        raise CollabError("未知の pubkey_id: {}".format(manifest.get("pubkey_id")))

    # 1) manifest 自体の署名（manifest 改変・期限書換え・流用を弾く）
    if not _verify_rsa(manifest_raw, sig, pubkey):
        raise CollabError("署名が一致しません")
    # 2) mode.py の中身が manifest の sha256 と一致するか（本体改変を弾く）
    if hashlib.sha256(mode_src).hexdigest() != manifest.get("sha256"):
        raise CollabError("mode.py のハッシュが一致しません")

    return manifest, mode_src.decode("utf-8")


# --- インストール先（アプリ管理フォルダ。ユーザーは触らない） -----------------

def installed_dir():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/1f")
    else:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                            "1f")
    return os.path.join(base, "installed")


def _state_path(key):
    return os.path.join(installed_dir(), key + ".state")


def _read_first_seen(key, today):
    """初回確認日（無ければ今日を記録して返す）"""
    p = _state_path(key)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return _parse_date(json.load(f)["first_seen"])
    except (OSError, ValueError, KeyError, TypeError):
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"first_seen": today.isoformat()}, f)
        except OSError:
            pass
        return today


def effective_expiry(manifest, first_seen):
    """有効期限（min(until, first_seen+max_days)）。無期限なら None"""
    ends = []
    av = manifest.get("available") or {}
    if av.get("until"):
        try:
            ends.append(_parse_date(av["until"]))
        except (ValueError, TypeError):
            pass
    md = manifest.get("max_days") or 0
    if md > 0:
        ends.append(first_seen + datetime.timedelta(days=int(md)))
    return min(ends) if ends else None


def _delete_package(key):
    for p in (os.path.join(installed_dir(), key + ".1fmode"), _state_path(key)):
        try:
            os.remove(p)
        except OSError:
            pass


def scan_installed(today=None):
    """installed/ の .1fmode を検証・期限判定して、

    returns (entries, expired)
      entries: [(manifest, mode_source, expiry|None), ...]  今読み込むべき有効なもの
      expired: [表示名, ...]  今回期限切れで削除したもの（通知用）

    - 署名/整合性NG: 黙って無視（壊れた配布物・改ざん）
    - 期間前(from より前): 保持するが読み込まない
    - 期間内: 読み込む
    - 期限切れ: ファイルごと削除し expired に積む
    """
    today = today or datetime.date.today()
    d = installed_dir()
    entries, expired = [], []
    if not os.path.isdir(d):
        return entries, expired
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".1fmode"):
            continue
        path = os.path.join(d, fn)
        try:
            manifest, src = load_and_verify(path)
        except CollabError:
            continue  # 不正パッケージは無視
        key = manifest.get("key") or fn[:-7]
        av = manifest.get("available") or {}
        # 開始前: まだ出さない（削除もしない）
        if av.get("from"):
            try:
                if today < _parse_date(av["from"]):
                    continue
            except (ValueError, TypeError):
                pass
        first_seen = _read_first_seen(key, today)
        exp = effective_expiry(manifest, first_seen)
        if exp is not None and today > exp:
            name = (manifest.get("name") or {}).get("ja") \
                or (manifest.get("name") or {}).get("en") or key
            _delete_package(key)
            expired.append(name)
            continue
        entries.append((manifest, src, exp))
    return entries, expired


def fetch_trial(url):
    """お試し用にパッケージを取得して署名検証し、(key, mode_source) を返す。
    installed/ には保存しない（試用は一時的）。検証NG/取得失敗は CollabError。"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "1f-app"})
        data = urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        raise CollabError("取得失敗: {!r}".format(e))
    tmp = io.BytesIO(data)
    try:
        with zipfile.ZipFile(tmp) as z:
            manifest_raw = z.read("manifest.json")
            sig = z.read("manifest.sig")
            mode_src = z.read("mode.py")
    except (zipfile.BadZipFile, KeyError) as e:
        raise CollabError("壊れたパッケージ: {!r}".format(e))
    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise CollabError("manifest が不正: {!r}".format(e))
    pubkey = COLLAB_PUBKEYS.get(manifest.get("pubkey_id"))
    if not pubkey or not _verify_rsa(manifest_raw, sig, pubkey):
        raise CollabError("署名が一致しません")
    if hashlib.sha256(mode_src).hexdigest() != manifest.get("sha256"):
        raise CollabError("mode.py のハッシュが一致しません")
    return manifest.get("key"), mode_src.decode("utf-8")


def list_installed(today=None):
    """インストール済みコラボシーンの一覧（入手済み管理UI用）。
    returns [{key, name, expiry(date|None), days_left(int|None), valid(bool)}]"""
    today = today or datetime.date.today()
    d = installed_dir()
    out = []
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".1fmode"):
            continue
        path = os.path.join(d, fn)
        try:
            manifest, _ = load_and_verify(path)
        except CollabError:
            continue
        key = manifest.get("key") or fn[:-7]
        name = (manifest.get("name") or {})
        first_seen = _read_first_seen(key, today)
        exp = effective_expiry(manifest, first_seen)
        days_left = (exp - today).days if exp else None
        out.append({
            "key": key,
            "name": name,
            "expiry": exp,
            "days_left": days_left,
            "perpetual": exp is None,       # 期限なし＝恒常（買い切り/無料恒常）
            "price": manifest.get("price", 0),
            "valid": exp is None or today <= exp,
        })
    return out


def uninstall(key):
    """ユーザーが入手済みシーンを手動で削除する"""
    _delete_package(key)


def fetch_catalog(url):
    """配布カタログ（JSON 配列）を取得する。各要素:
      {key, name:{ja,en}, desc:{ja,en}, available:{from,until}, url, price?}
    取得失敗・未設定は空リスト（ストア未稼働でも UI が壊れない）。"""
    url = url or DEFAULT_CATALOG_URL
    if not url:
        return []
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "1f-app"})
        data = urllib.request.urlopen(req, timeout=15).read()
        cat = json.loads(data.decode("utf-8"))
        return cat if isinstance(cat, list) else cat.get("scenes", [])
    except Exception:
        return []


def _canon(payload):
    """署名対象の正規化バイト列（ツールと完全一致させること）"""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def fetch_and_apply_revocations(url=None):
    """署名付き失効リストを取得・検証し、該当する installed シーンを削除する。

    失効リスト形式（1ファイル）:
      {"payload": {"format":1, "revoked":["key1",...], "issued":"YYYY-MM-DD",
                   "pubkey_id":1}, "sig": "<base64>"}
    returns 削除した表示名のリスト（通知用）。取得失敗・署名NG・未配置は []（安全側）。
    オフライン時は何もしない（次にオンラインになったとき適用される）。
    """
    import base64
    import urllib.request
    url = url or DEFAULT_REVOKE_URL
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "1f-app"})
        doc = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        payload = doc["payload"]
        sig = base64.b64decode(doc["sig"])
    except Exception:
        return []  # オフライン・404・壊れ → 何もしない
    pubkey = COLLAB_PUBKEYS.get(payload.get("pubkey_id"))
    if not pubkey or not _verify_rsa(_canon(payload), sig, pubkey):
        return []  # 署名NG（改ざん）→ 無視
    revoked = set(payload.get("revoked") or [])
    if not revoked:
        return []
    removed = []
    d = installed_dir()
    if not os.path.isdir(d):
        return []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".1fmode"):
            continue
        try:
            manifest, _ = load_and_verify(os.path.join(d, fn))
        except CollabError:
            continue
        key = manifest.get("key") or fn[:-7]
        if key in revoked:
            name = (manifest.get("name") or {}).get("ja") \
                or (manifest.get("name") or {}).get("en") or key
            _delete_package(key)
            removed.append(name)
    return removed


def update_installed(catalog_url=None):
    """インストール済みシーンを、カタログの最新版に自動更新する。

    カタログ各エントリの sha256（mode.py のハッシュ）と、インストール済み
    パッケージの manifest.sha256 を比較し、違えば再ダウンロードして置き換える。
    → 配信後（ユーザーがインストール後）でも、作者がシーンを直して再配信すれば
    次回起動時に全員が自動で最新版になる。期限の起点(first_seen)は維持。
    returns 更新したシーンの key リスト。"""
    cat = fetch_catalog(catalog_url)
    by_key = {c.get("key"): c for c in cat if c.get("key")}
    if not by_key:
        return []
    d = installed_dir()
    if not os.path.isdir(d):
        return []
    updated = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".1fmode"):
            continue
        try:
            manifest, _ = load_and_verify(os.path.join(d, fn))
        except CollabError:
            continue
        key = manifest.get("key")
        c = by_key.get(key)
        if not c or not c.get("sha256"):
            continue
        if c["sha256"] != manifest.get("sha256"):
            try:
                install_scene(c["url"])   # 検証して上書き（.state は保持）
                updated.append(key)
            except Exception:
                pass
    return updated


def install_scene(url, dest_name=None):
    """URL（http/https/file）から .1fmode を取得し、検証して installed/ に保存。
    成功すれば manifest を返す。ユーザー操作は「入手」ボタン1つの想定。"""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "1f-app"})
    data = urllib.request.urlopen(req, timeout=30).read()
    # 一旦メモリ上で検証してから保存（不正なものをディスクに残さない）
    tmp = io.BytesIO(data)
    try:
        with zipfile.ZipFile(tmp) as z:
            manifest = json.loads(z.read("manifest.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError) as e:
        raise CollabError("取得したパッケージが不正: {!r}".format(e))
    key = manifest.get("key")
    if not key:
        raise CollabError("manifest に key がありません")
    os.makedirs(installed_dir(), exist_ok=True)
    path = os.path.join(installed_dir(), (dest_name or key) + ".1fmode")
    with open(path, "wb") as f:
        f.write(data)
    # 保存後に正式検証（NGなら消す）
    try:
        load_and_verify(path)
    except CollabError:
        try:
            os.remove(path)
        except OSError:
            pass
        raise
    return manifest
