"""みんなのお気に入りモード（人気投票）の送信・取得。

オプトイン（config の stats_optin）時のみ使われる。
送信するのは匿名ID（uuid4 hex）とお気に入りモード名のリストだけで、
個人情報は一切含まない。通信失敗は黙って無視する（callback に None）。
"""
import json
import threading
import urllib.request

# 集計サーバ（Cloudflare Pages Functions + D1）。config の "stats_url" で上書き可能
DEFAULT_STATS_URL = "https://1f-stats.pages.dev"
TIMEOUT = 8


def _request(url, data=None, callback=None):
    def run():
        result = None
        try:
            # Cloudflare はデフォルトの Python-urllib UA を 403 で弾く
            headers = {"User-Agent": "1f-app"}
            if data:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                result = json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
        if callback:
            callback(result)
    threading.Thread(target=run, daemon=True).start()


def submit_favorites(uid, scenes, base_url=None, callback=None):
    """お気に入りを投票し、最新の集計 {users, counts} を callback に渡す（別スレッド）"""
    data = json.dumps({"uid": uid, "scenes": list(scenes)}).encode("utf-8")
    _request((base_url or DEFAULT_STATS_URL) + "/favorites", data, callback)


def fetch_stats(base_url=None, callback=None):
    """集計 {users, counts} を取得して callback に渡す（別スレッド）"""
    _request((base_url or DEFAULT_STATS_URL) + "/stats", None, callback)


def submit_usage(uid, scene, base_url=None, callback=None):
    """利用記録（1人×1モード×1日でサーバ側upsert）を送信（別スレッド）"""
    data = json.dumps({"uid": uid, "scene": scene}).encode("utf-8")
    _request((base_url or DEFAULT_STATS_URL) + "/usage", data, callback)


def submit_errlog(payload, base_url=None, callback=None):
    """同意済みの匿名エラーログ {ver, skeleton, platform, os, log} を送信（別スレッド）"""
    data = json.dumps(payload).encode("utf-8")
    _request((base_url or DEFAULT_STATS_URL) + "/errlog", data, callback)
