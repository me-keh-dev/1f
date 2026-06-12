"""リリース公開ツール: code.zip と version.json を生成して Cloudflare Pages へ配置。

使い方:
  python tools/publish_update.py                # 生成のみ (dist_update/ へ出力)
  python tools/publish_update.py --upload       # 生成 + Cloudflare Pages へデプロイ

version.py の CODE_VERSION を上げてから実行すること。
コア（exe）も更新した場合は --installer dist/1f.exe を指定し、
bootstrap.py の SKELETON_VERSION に合わせて --skeleton を指定する。
installer 本体は GitHub Releases に置き、--installer-url でそのURLを渡す。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from version import CODE_VERSION  # noqa: E402

# 差し替え可能なアプリコード（1f.spec の APP_CODE と同期すること）
CODE_FILES = [
    "main.py", "i18n.py", "weather.py", "weather_fx.py",
    "platform_win.py", "platform_mac.py", "audio_level.py",
    "version.py", "updater.py", "stats.py",
]
CODE_DIRS = ["scenes"]

OUT_DIR = os.path.join(ROOT, "dist_update")

# ---- 配信先（Cloudflare Pages） ---------------------------------------------
CF_PROJECT = "1f-updates"
BASE_URL = "https://1f-updates.pages.dev"
# このコードが動作するのに必要な最小スケルトン版
MIN_SKELETON = 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_code_zip():
    os.makedirs(OUT_DIR, exist_ok=True)
    zip_name = "code-{}.zip".format(CODE_VERSION)
    zip_path = os.path.join(OUT_DIR, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODE_FILES:
            p = os.path.join(ROOT, f)
            if not os.path.isfile(p):
                raise SystemExit("missing: " + f)
            z.write(p, f)
        for d in CODE_DIRS:
            for root, _, files in os.walk(os.path.join(ROOT, d)):
                if "__pycache__" in root:
                    continue
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, ROOT).replace(os.sep, "/"))
    return zip_path, zip_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true",
                    help="Cloudflare Pages へデプロイ")
    ap.add_argument("--installer", help="コア更新用 exe のパス（例: dist/1f.exe）")
    ap.add_argument("--installer-url", help="installer のURL（GitHub Releases等）")
    ap.add_argument("--skeleton", type=int, default=MIN_SKELETON,
                    help="最新スケルトン版（bootstrap.SKELETON_VERSION）")
    ap.add_argument("--notes", default="", help="更新内容の説明")
    args = ap.parse_args()

    zip_path, zip_name = build_code_zip()
    info = {
        "code_version": CODE_VERSION,
        "code_url": "{}/{}".format(BASE_URL.rstrip("/"), zip_name) if BASE_URL else zip_name,
        "code_sha256": sha256_file(zip_path),
        "min_skeleton": MIN_SKELETON,
        "skeleton_version": args.skeleton,
        "notes": args.notes,
    }
    if args.installer:
        info["installer_sha256"] = sha256_file(args.installer)
        info["installer_url"] = args.installer_url or ""
    elif args.installer_url:
        info["installer_url"] = args.installer_url

    vj = os.path.join(OUT_DIR, "version.json")
    with open(vj, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print("generated:")
    print("  " + zip_path)
    print("  " + vj)
    print(json.dumps(info, ensure_ascii=False, indent=2))

    if args.upload:
        subprocess.check_call(
            ["npx", "wrangler", "pages", "deploy", OUT_DIR,
             "--project-name", CF_PROJECT, "--branch", "main",
             "--commit-dirty=true"],
            shell=(os.name == "nt"))
        print("deployed to {}".format(BASE_URL))


if __name__ == "__main__":
    main()
