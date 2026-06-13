# -*- coding: utf-8 -*-
"""署名付きシーンパッケージ（.1fmode）を作る。

秘密鍵（private_scenes/_keys/collab_priv.pem）を持つ環境でのみ実行できる。
署名は openssl を呼ぶだけなので追加ライブラリ不要。
（このスクリプト自体は公開でOK＝鍵さえ秘密なら署名ロジックは秘密でない。）

usage:
  python tools/sign_scene.py <mode.py> --until 2026-07-31 \
      [--from 2026-07-01] [--max-days 30] [--pubkey-id 1] \
      [--key private_scenes/_keys/collab_priv.pem] [-o out.1fmode]

mode.py は SCENE 契約を満たすシーン1個（key/label_key/class/texts を持つこと）。
"""
import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KEY = os.path.join(ROOT, "private_scenes", "_keys", "collab_priv.pem")


def _scene_meta_from_source(src, path):
    """mode.py を実行せず AST から SCENE の key と name(ja/en) を取り出す。
    （任意コード実行を避けるため、SCENE 辞書のリテラル部分だけ読む）"""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SCENE" for t in node.targets):
            if not isinstance(node.value, ast.Dict):
                break
            d = {}
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(k, ast.Constant):
                    try:
                        d[k.value] = ast.literal_eval(v)
                    except (ValueError, SyntaxError):
                        d[k.value] = None
            return d
    raise SystemExit("SCENE 辞書が見つかりません: " + path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", help="シーンの .py（SCENE 契約）")
    ap.add_argument("--until", help="終了日 YYYY-MM-DD（この日まで有効）")
    ap.add_argument("--from", dest="from_", help="開始日 YYYY-MM-DD（任意）")
    ap.add_argument("--max-days", type=int, default=0,
                    help="初回インストールから N 日で失効（0=無期限。until と早い方）")
    ap.add_argument("--pubkey-id", type=int, default=1)
    ap.add_argument("--key", default=DEFAULT_KEY, help="署名用の秘密鍵 PEM")
    ap.add_argument("-o", "--out", help="出力 .1fmode（既定: <key>.1fmode）")
    args = ap.parse_args()

    if not os.path.isfile(args.key):
        raise SystemExit("秘密鍵がありません: {}\n（鍵を持つ環境で実行してください）"
                         .format(args.key))
    src = open(args.mode, "rb").read()
    meta = _scene_meta_from_source(src.decode("utf-8"), args.mode)
    key = meta.get("key")
    if not key:
        raise SystemExit("SCENE['key'] がありません")

    # name は texts から日英を拾う（一覧・通知に使う）
    texts = meta.get("texts") or {}
    label_key = meta.get("label_key", "")
    name = {
        "ja": (texts.get("ja") or {}).get(label_key, key),
        "en": (texts.get("en") or {}).get(label_key, key),
    }

    available = {}
    if args.from_:
        available["from"] = args.from_
    if args.until:
        available["until"] = args.until

    manifest = {
        "format": 1,
        "key": key,
        "sha256": hashlib.sha256(src).hexdigest(),
        "name": name,
        "available": available,
        "max_days": args.max_days,
        "pubkey_id": args.pubkey_id,
    }
    manifest_raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")

    # openssl で manifest を署名
    with tempfile.TemporaryDirectory() as td:
        mpath = os.path.join(td, "manifest.json")
        spath = os.path.join(td, "manifest.sig")
        with open(mpath, "wb") as f:
            f.write(manifest_raw)
        subprocess.check_call(
            ["openssl", "dgst", "-sha256", "-sign", args.key, "-out", spath, mpath])
        sig = open(spath, "rb").read()

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.mode)),
                                   key + ".1fmode")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mode.py", src)
        z.writestr("manifest.json", manifest_raw)
        z.writestr("manifest.sig", sig)
    print("signed:", out)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
