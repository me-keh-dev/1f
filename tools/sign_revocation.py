# -*- coding: utf-8 -*-
"""失効リスト（revoked.json）を作る — 配布済みシーンを後から停止する。

権利問題・規約違反・リコール等で、買い切り（永続）を含む任意のシーンを
全ユーザーの端末から削除させる。生成した revoked.json を Cloudflare
（version.json と同じ場所）に置くと、各アプリが取得・署名検証して該当
シーンを削除する。秘密鍵を持つ環境でのみ実行できる（署名は openssl）。

usage:
  python tools/sign_revocation.py --revoke key1 key2 ... \
      [--issued 2026-07-01] [--pubkey-id 1] \
      [--key private_scenes/_keys/collab_priv.pem] [-o dist_update/revoked.json]

出力した revoked.json を `wrangler pages deploy` で配信する。
失効を解除する（再び使えるようにする）には、その key を外したリストを再配信。
ただし既に削除されたユーザーは再入手が必要（LINEの再ダウンロードと同様）。
"""
import argparse
import base64
import json
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KEY = os.path.join(ROOT, "private_scenes", "_keys", "collab_priv.pem")
DEFAULT_OUT = os.path.join(ROOT, "dist_update", "revoked.json")


def canon(payload):
    """scenes/_collab.py の _canon と完全一致させること"""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revoke", nargs="*", default=[],
                    help="失効させるシーンの key（複数可）")
    ap.add_argument("--issued", help="発行日 YYYY-MM-DD（記録用）")
    ap.add_argument("--pubkey-id", type=int, default=1)
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    if not os.path.isfile(args.key):
        raise SystemExit("秘密鍵がありません: {}".format(args.key))

    payload = {
        "format": 1,
        "revoked": sorted(set(args.revoke)),
        "issued": args.issued or "",
        "pubkey_id": args.pubkey_id,
    }
    raw = canon(payload)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "payload")
        s = os.path.join(td, "sig")
        with open(p, "wb") as f:
            f.write(raw)
        subprocess.check_call(
            ["openssl", "dgst", "-sha256", "-sign", args.key, "-out", s, p])
        sig = open(s, "rb").read()

    doc = {"payload": payload, "sig": base64.b64encode(sig).decode("ascii")}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("wrote:", args.out)
    print("revoked:", payload["revoked"] or "(none — clears the list)")


if __name__ == "__main__":
    main()
