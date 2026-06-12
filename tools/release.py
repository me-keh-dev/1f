"""リリース自動振り分けツール。

変更されたパスから「どのリリース手順が必要か」を判定し、確認プロンプト付きで実行する。

  ルートA: private_scenes/ のみの変更
    → private リポジトリへ commit+push、CODE_VERSION を上げて
      公開リポジトリに version.py だけの極小コミット、コード配信（exe不要）
  ルートB: エンジン（公開側 .py など）の変更
    → 公開リポジトリへ commit+push ＋ CODE_VERSION ↑ ＋ コード配信
  ルートC: 骨格の変更（bootstrap.py / SKELETON_VERSION / 新ライブラリ＝requirements.txt / spec）
    → ルートBに加えて exe 再ビルド → GitHub Release → --installer --skeleton 付き配信

使い方:
  python tools/release.py            # 判定と実行（各ステップで確認）
  python tools/release.py --dry-run  # 判定だけ表示して何もしない
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(ROOT, "private_scenes")
VERSION_FILE = os.path.join(ROOT, "version.py")

# このどれかが変わっていたら「骨格」扱い（exe 再ビルド＋GitHub Release が必要）
# spec は次回ビルドにしか効かないため骨格には含めない（エンジン扱い）
SKELETON_FILES = {"bootstrap.py", "requirements.txt"}


def run(cmd, cwd=ROOT, capture=False):
    print("  $ " + " ".join(cmd))
    if capture:
        return subprocess.check_output(cmd, cwd=cwd, encoding="utf-8",
                                       errors="replace")
    subprocess.check_call(cmd, cwd=cwd)


def git_changes(cwd):
    """git status --porcelain の変更パス一覧（untracked 含む）"""
    out = subprocess.check_output(["git", "status", "--porcelain"], cwd=cwd,
                                  encoding="utf-8", errors="replace")
    paths = []
    for line in out.splitlines():
        if not line.strip():
            continue
        p = line[3:].strip().strip('"')
        if " -> " in p:  # rename
            p = p.split(" -> ")[1]
        paths.append(p.replace("\\", "/"))
    return paths


def confirm(msg):
    ans = input("{} [y/N] ".format(msg)).strip().lower()
    return ans in ("y", "yes")


def current_version():
    text = open(VERSION_FILE, encoding="utf-8").read()
    m = re.search(r'CODE_VERSION\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("version.py から CODE_VERSION を読めません")
    return m.group(1)


def bump_version(kind):
    """CODE_VERSION を上げる（kind: 'patch' or 'minor'）。確認の上で書き換える"""
    cur = current_version()
    parts = cur.split(".")
    while len(parts) < 3:
        parts.append("0")
    major, minor, patch = (int(x) for x in parts[:3])
    if kind == "minor":
        suggest = "{}.{}.0".format(major, minor + 1)
    else:
        suggest = "{}.{}.{}".format(major, minor, patch + 1)
    new = input("新しい CODE_VERSION [{} → {}]（Enterで採用 / 任意入力可）: "
                .format(cur, suggest)).strip() or suggest
    text = open(VERSION_FILE, encoding="utf-8").read()
    text = text.replace('CODE_VERSION = "{}"'.format(cur),
                        'CODE_VERSION = "{}"'.format(new))
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print("  version.py: {} → {}".format(cur, new))
    return new


def commit_push(cwd, message, label):
    print("\n--- {} の変更 ---".format(label))
    run(["git", "status", "--short"], cwd=cwd)
    if not confirm("{} を commit して push しますか？".format(label)):
        return False
    run(["git", "add", "-A"], cwd=cwd)
    run(["git", "commit", "-m", message], cwd=cwd)
    run(["git", "push"], cwd=cwd)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="判定のみ")
    ap.add_argument("--notes", default="", help="更新内容（version.json の notes）")
    args = ap.parse_args()

    public = [p for p in git_changes(ROOT) if not p.startswith("private_scenes/")]
    private = git_changes(PRIVATE_DIR) if os.path.isdir(
        os.path.join(PRIVATE_DIR, ".git")) else []

    # 配信対象外のローカルファイルを無視（画像・zip 等の作業ファイル）
    IGNORED_EXT = (".png", ".jpg", ".jpeg", ".zip", ".txt", ".pdf")
    noise = [p for p in public if p.lower().endswith(IGNORED_EXT)]
    public = [p for p in public if p not in noise]

    skeleton = sorted(set(public) & SKELETON_FILES)
    engine = [p for p in public if p not in SKELETON_FILES]

    print("変更の内訳:")
    print("  骨格        :", skeleton or "なし")
    print("  エンジン    :", engine or "なし")
    print("  private     :", private or "なし")
    if noise:
        print("  無視(作業ファイル):", noise)

    if skeleton:
        route = "C"
    elif engine:
        route = "B"
    elif private:
        route = "A"
    else:
        print("変更がありません。")
        return

    print("\n→ ルート{}: {}".format(route, {
        "A": "private のみ（privateへpush → CODE_VERSION↑ → コード配信。exe不要）",
        "B": "エンジン変更（公開push → CODE_VERSION↑ → コード配信）",
        "C": "骨格変更（公開push → exe再ビルド → GitHub Release → --installer 配信）",
    }[route]))
    if args.dry_run:
        return

    notes = args.notes or input("更新内容（notes）: ").strip()

    # 1) private リポジトリ
    if private:
        commit_push(PRIVATE_DIR, notes or "Update private scenes", "private_scenes")

    # 2) CODE_VERSION を上げる（モードだけの変更でも公開側 version.py の
    #    極小コミットが必要＝現行更新方式の都合）
    if confirm("CODE_VERSION を上げますか？"):
        bump_version("minor" if route == "C" else "patch")

    # 3) 公開リポジトリ
    if git_changes(ROOT):
        pub_changed = [p for p in git_changes(ROOT)
                       if not p.startswith("private_scenes/")
                       and not p.lower().endswith(IGNORED_EXT)]
        if pub_changed:
            commit_push(ROOT, notes or "Release", "公開リポジトリ")

    # 4) 配信
    if route == "C":
        ver = current_version()
        print("\n骨格が変わっています。以下を手動で実行してください:")
        print("  1. bootstrap.py の SKELETON_VERSION を上げたか確認")
        print("  2. pyinstaller 1f.spec → dist/1f.exe を起動確認")
        print("  3. GitHub Release v{} を作成して 1f.exe を添付".format(ver))
        print("  4. python tools/publish_update.py --upload --notes \"{}\" \\".format(notes))
        print("       --installer dist/1f.exe --installer-url <ReleaseのexeURL> --skeleton <版>")
        return

    if confirm("コード配信（publish_update --upload）を実行しますか？"):
        run([sys.executable, os.path.join("tools", "publish_update.py"),
             "--upload", "--notes", notes])


if __name__ == "__main__":
    main()
