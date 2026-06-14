# -*- coding: utf-8 -*-
"""シーン商品台帳 → 配信物（カタログ・署名済みパッケージ・失効リスト）を生成。

商品台帳 private_scenes/_store/products.json を読み、
  - status=published のシーン → 署名して dist_update/scenes/<key>.1fmode、
    かつ catalog.json に掲載
  - status=discontinued のシーン → revoked.json に載せて全ユーザーから停止
  - status=draft のシーン → 何もしない（編集中）
を生成する。出力は dist_update/。あとは `wrangler pages deploy` で配信。

秘密鍵を持つ環境でのみ実行できる（sign_scene.py / sign_revocation.py を呼ぶ）。

usage:
  python tools/build_store.py                      # 生成のみ
  python tools/build_store.py --registry path.json # 台帳を指定

商品台帳のスキーマ（1シーン）:
  {
    "key": "...", "name": {"ja","en"}, "desc": {"ja","en"},
    "price": 0,                       # 円。0=無料
    "available": {"from","until"} | null,   # null/省略=恒常（期限なし）
    "max_days": 0,                    # 初回DLからN日（0=無期限）
    "creator": "...", "status": "draft|published|discontinued",
    "source": "<_store/sources 内の .py>",
    "pubkey_id": 1
  }
有料/コラボのソースは _store/sources/（配信されない場所）に置くこと。
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(ROOT, "private_scenes", "_store")
DEFAULT_REGISTRY = os.path.join(STORE_DIR, "products.json")
DEFAULT_CREATORS = os.path.join(STORE_DIR, "creators.json")
SOURCES_DIR = os.path.join(STORE_DIR, "sources")
OUT_DIR = os.path.join(ROOT, "dist_update")
SCENES_OUT = os.path.join(OUT_DIR, "scenes")


def _sign_scene(src_path, out_path, price, available, max_days, pubkey_id):
    cmd = [sys.executable, os.path.join(ROOT, "tools", "sign_scene.py"),
           src_path, "--price", str(price), "--max-days", str(max_days),
           "--pubkey-id", str(pubkey_id), "-o", out_path]
    av = available or {}
    if av.get("from"):
        cmd += ["--from", av["from"]]
    if av.get("until"):
        cmd += ["--until", av["until"]]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)


def _load_creators(path):
    """クリエイター台帳を id -> creator の辞書で返す（無ければ空）"""
    if not os.path.isfile(path):
        return {}
    data = json.load(open(path, encoding="utf-8"))
    return {c["id"]: c for c in data.get("creators", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--creators", default=DEFAULT_CREATORS)
    args = ap.parse_args()

    if not os.path.isfile(args.registry):
        raise SystemExit("商品台帳がありません: " + args.registry)
    reg = json.load(open(args.registry, encoding="utf-8"))
    base = (reg.get("base_url") or "").rstrip("/")
    scenes = reg.get("scenes", [])
    creators = _load_creators(args.creators)

    os.makedirs(SCENES_OUT, exist_ok=True)
    catalog, revoked = [], []
    pubkey_id = 1

    for s in scenes:
        key = s["key"]
        status = s.get("status", "draft")
        pubkey_id = s.get("pubkey_id", 1)
        if status == "discontinued":
            revoked.append(key)
            continue
        if status != "published":
            continue  # draft 等は無視
        # クリエイター登録チェック: 未登録/停止中のクリエイターは公開できない
        cid = s.get("creator_id")
        cr = creators.get(cid)
        if not cr:
            raise SystemExit(
                "{}: creator_id={!r} がクリエイター台帳に未登録です（公開不可）"
                .format(key, cid))
        if cr.get("status") != "active":
            raise SystemExit(
                "{}: クリエイター {!r} は status={} のため公開できません"
                .format(key, cid, cr.get("status")))
        src = os.path.join(SOURCES_DIR, s["source"])
        if not os.path.isfile(src):
            raise SystemExit("source が見つかりません: {} ({})".format(src, key))
        out = os.path.join(SCENES_OUT, key + ".1fmode")
        _sign_scene(src, out, s.get("price", 0), s.get("available"),
                    s.get("max_days", 0), pubkey_id)
        # mode.py のハッシュ（manifest.sha256 と同値）。インストール済みの
        # 自動更新判定に使う（中身が変われば全ユーザーが次回起動で取り直す）
        import hashlib as _hl
        src_sha = _hl.sha256(open(src, "rb").read()).hexdigest()
        entry = {
            "key": key,
            "name": s.get("name", {}),
            "desc": s.get("desc", {}),
            "price": s.get("price", 0),
            "sha256": src_sha,
            "url": "{}/scenes/{}.1fmode".format(base, key) if base
                   else "scenes/{}.1fmode".format(key),
        }
        if s.get("available"):
            entry["available"] = s["available"]
        catalog.append(entry)

    # カタログ
    with open(os.path.join(OUT_DIR, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    # 失効リスト（discontinued があれば署名生成）
    if revoked:
        subprocess.check_call(
            [sys.executable, os.path.join(ROOT, "tools", "sign_revocation.py"),
             "--revoke", *revoked, "--pubkey-id", str(pubkey_id),
             "-o", os.path.join(OUT_DIR, "revoked.json")],
            stdout=subprocess.DEVNULL)

    print("built:")
    print("  published:", [e["key"] for e in catalog] or "(none)")
    print("  discontinued:", revoked or "(none)")
    print("  -> {}/catalog.json".format(OUT_DIR))
    print("     {}/scenes/*.1fmode".format(OUT_DIR))
    if revoked:
        print("     {}/revoked.json".format(OUT_DIR))
    print("\nデプロイ: cd dist_update && npx wrangler pages deploy . "
          "--project-name 1f-updates --branch main --commit-dirty=true")


if __name__ == "__main__":
    main()
