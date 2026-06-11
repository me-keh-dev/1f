"""スマホゲーム式の自動更新。

起動時にサーバの version.json へ差分を確認し、
- コード差分（差し替え可能な .py 群の zip）: 自動DL → SHA256検証 →
  %APPDATA%/1f/code へ展開（bootstrap が次回起動時に優先ロード）→ 再起動を提案
- コア更新（スケルトン exe が変わる）: 同意ダイアログ → DL → SHA256検証 →
  バッチで自己置換 → 自動再起動
- MSIX（ストア）版: コード/exe のダウンロードは一切行わず、ストアでの
  更新を案内するのみ（Microsoft Store ポリシー 10.2 / App Store 2.5.2 準拠）

version.json の形式:
{
  "code_version": "2.9.1",      // 最新コード版
  "code_url": "https://.../code-2.9.1.zip",
  "code_sha256": "...",
  "min_skeleton": 1,            // このコードが要求するスケルトン版
  "skeleton_version": 1,        // 最新スケルトン版（上がるとコア更新）
  "installer_url": "https://.../1f.exe",
  "installer_sha256": "...",
  "notes": "更新内容の説明"
}
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

from i18n import t
from version import CODE_VERSION

# 配信サーバ（Cloudflare Pages）。config の "update_url" で上書き可能
DEFAULT_UPDATE_URL = "https://1f-updates.pages.dev/version.json"

_refs = []   # シグナル接続中オブジェクトのGC防止


def _ver_tuple(v):
    try:
        return tuple(int(p) for p in str(v).strip().lstrip("v").split("."))
    except ValueError:
        return (0,)


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def is_store_build():
    """MSIX(Microsoft Store)配布かどうか。ストア版はストア外更新を行わない"""
    return (is_frozen() and sys.platform == "win32"
            and "windowsapps" in sys.executable.lower())


def skeleton_version():
    """exe（スケルトン）の版。bootstrap が環境変数で渡す。旧exeは0"""
    try:
        return int(os.environ.get("ONEF_SKELETON_VERSION", "0"))
    except ValueError:
        return 0


def external_code_dir():
    # bootstrap.external_code_dir() と同一仕様
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/1f")
    else:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "1f")
    return os.path.join(base, "code")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class UpdateChecker(QObject):
    info_ready = pyqtSignal(dict)

    def check(self, url):
        threading.Thread(target=self._fetch, args=(url,), daemon=True).start()

    def _fetch(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "1f-updater"})
            with urllib.request.urlopen(req, timeout=8) as r:
                self.info_ready.emit(json.loads(r.read().decode("utf-8")))
        except Exception:
            pass   # オフライン等は通常起動（次回再試行）


class _Downloader(QObject):
    progress = pyqtSignal(int, int)   # (受信済み, 合計)
    finished = pyqtSignal(str)        # 一時ファイルパス（"" = 失敗/検証NG）

    def __init__(self, url, sha256):
        super().__init__()
        self.url = url
        self.sha256 = (sha256 or "").lower()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        path = ""
        tmp = ""
        try:
            fd, tmp = tempfile.mkstemp(prefix="1f_update_")
            os.close(fd)
            req = urllib.request.Request(self.url,
                                         headers={"User-Agent": "1f-updater"})
            with urllib.request.urlopen(req, timeout=30) as r, \
                    open(tmp, "wb") as out:
                total = int(r.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    self.progress.emit(done, total)
            # 改ざん・破損防止: SHA256必須
            if self.sha256 and _sha256_file(tmp) == self.sha256:
                path = tmp
        except Exception:
            pass
        if not path and tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
        self.finished.emit(path)


def _apply_code_zip(zip_path):
    """code.zip を外部コードディレクトリへアトミックに展開"""
    ext = external_code_dir()
    new_dir = ext + ".new"
    old_dir = ext + ".old"
    for d in (new_dir, old_dir):
        shutil.rmtree(d, ignore_errors=True)
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            p = os.path.normpath(m)
            if p.startswith("..") or os.path.isabs(p):
                raise ValueError("unsafe path in zip")
        z.extractall(new_dir)
    if not os.path.isfile(os.path.join(new_dir, "main.py")):
        raise ValueError("main.py missing in code zip")
    if os.path.isdir(ext):
        os.rename(ext, old_dir)
    os.rename(new_dir, ext)
    shutil.rmtree(old_dir, ignore_errors=True)


def _restart():
    if is_frozen():
        subprocess.Popen([sys.executable], close_fds=True)
    else:
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
    QApplication.quit()


def _launch_replacer(new_exe):
    """終了を待って exe を置換・再起動するバッチを切り離して起動（Windows）"""
    exe = sys.executable
    pid = os.getpid()
    bat = os.path.join(tempfile.gettempdir(), "1f_update.bat")
    with open(bat, "w", encoding="ascii", errors="replace") as f:
        f.write(
            '@echo off\r\n'
            ':wait\r\n'
            'tasklist /FI "PID eq {pid}" 2>nul | find " {pid} " >nul && '
            '(timeout /t 1 /nobreak >nul & goto wait)\r\n'
            'move /y "{new}" "{exe}" >nul\r\n'
            'start "" "{exe}"\r\n'
            'del "%~f0"\r\n'.format(pid=pid, new=new_exe, exe=exe))
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True)
    QApplication.quit()


def _do_code_update(info):
    """コード差分の自動DL→適用→再起動の提案"""
    dl = _Downloader(info.get("code_url", ""), info.get("code_sha256", ""))
    _refs.append(dl)

    def done(path):
        if not path:
            return   # 失敗はサイレント（次回起動時に再試行）
        try:
            _apply_code_zip(path)
        except Exception:
            return
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        ret = QMessageBox.question(
            None, t("update_title"),
            t("update_code_applied").format(ver=info.get("code_version", "")),
            QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            _restart()

    dl.finished.connect(done)
    dl.start()


def _ask_core_update(info):
    """コア（exe）更新: 同意→DL（進捗表示）→検証→自己置換→再起動"""
    ver = info.get("code_version", "")
    msg = t("update_core_ask").format(ver=ver)
    notes = info.get("notes", "")
    if notes:
        msg += "\n\n" + notes
    if QMessageBox.question(None, t("update_title"), msg,
                            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
        return
    url = info.get("installer_url", "")
    if not url:
        return
    if sys.platform != "win32":
        import webbrowser
        webbrowser.open(url)
        return
    prog = QProgressDialog(t("update_downloading"), None, 0, 100)
    prog.setWindowTitle(t("update_title"))
    prog.setMinimumDuration(0)
    prog.setValue(0)
    dl = _Downloader(url, info.get("installer_sha256", ""))
    _refs.extend([dl, prog])

    def on_progress(done_b, total_b):
        if total_b:
            prog.setValue(min(100, int(done_b * 100 / total_b)))

    def done(path):
        prog.close()
        if not path:
            QMessageBox.warning(None, t("update_title"), t("update_failed"))
            return
        _launch_replacer(path)

    dl.progress.connect(on_progress)
    dl.finished.connect(done)
    dl.start()


def _handle_info(info):
    try:
        srv_code = info.get("code_version", "0")
        srv_skel = int(info.get("skeleton_version", 0))
        min_skel = int(info.get("min_skeleton", 0))
        local_skel = skeleton_version()
        need_code = _ver_tuple(srv_code) > _ver_tuple(CODE_VERSION)
        need_skel = srv_skel > local_skel
        if is_store_build():
            # ストア版: 案内のみ（ストア外からのコード取得・自己更新はしない）
            if need_code or need_skel:
                QMessageBox.information(
                    None, t("update_title"),
                    t("update_store").format(ver=srv_code))
            return
        if need_skel or (need_code and local_skel < min_skel):
            _ask_core_update(info)
        elif need_code:
            _do_code_update(info)
    except Exception:
        pass


def start_update_check(config):
    """起動数秒後に main() から呼ぶ。失敗はすべてサイレント"""
    if not config.get("auto_update", True):
        return
    # 開発実行（非frozen）では誤適用を防ぐためスキップ。
    # テストは ONEF_DEV_UPDATE=1 で強制実行できる
    if not is_frozen() and not os.environ.get("ONEF_DEV_UPDATE"):
        return
    url = config.get("update_url") or DEFAULT_UPDATE_URL
    if not url:
        return
    checker = UpdateChecker()
    _refs.append(checker)
    checker.info_ready.connect(_handle_info)
    checker.check(url)
