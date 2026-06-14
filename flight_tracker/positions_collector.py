# -*- coding: utf-8 -*-
"""positions_collector — OpenSky の全機スナップショットを raw_positions に蓄積。

- 既定 10分間隔（環境変数 POLL_INTERVAL_SEC）。匿名アクセスのレート（10秒）は
  10分間隔で十分に下回る。失敗時は指数的でない一定間隔リトライ（3回・30秒）。
- 本番は全球（bbox無し）。テスト時は FT_BBOX="lamin,lomin,lamax,lomax" で範囲限定。
- 軽量運用: states を逐次デコードしバッチ INSERT（全件をメモリ展開しない）。

データ出典: OpenSky Network (https://opensky-network.org/)。
※ OpenSky の規約は ODbL ではない。再配布/公開ダンプは規約確認まで行わない（内部利用）。
"""
import os
import sys
import time
import logging

import requests

from db import connect, init_db

OPENSKY_URL = os.environ.get(
    "OPENSKY_URL", "https://opensky-network.org/api/states/all")
DB_PATH = os.environ.get("FT_DB", "flight_tracker.db")
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "600"))   # 10分
RETRIES = int(os.environ.get("FT_RETRIES", "3"))
RETRY_WAIT_SEC = int(os.environ.get("FT_RETRY_WAIT_SEC", "30"))
USER_AGENT = "flight-tracker/0.1 (1f Flight Live View; +OpenSky)"

# OpenSky states ベクトルの位置インデックス（公式ドキュメント順）
# 0 icao24, 1 callsign, 2 origin_country, 3 time_position, 4 last_contact,
# 5 longitude, 6 latitude, 7 baro_altitude, 8 on_ground, 9 velocity,
# 10 true_track, 11 vertical_rate, ...

log = logging.getLogger("collector")


def fetch_states(bbox=None, timeout=30):
    """OpenSky /states/all を取得。bbox=(lamin,lomin,lamax,lomax) で範囲限定可。"""
    params = {}
    if bbox:
        params = {"lamin": bbox[0], "lomin": bbox[1],
                  "lamax": bbox[2], "lomax": bbox[3]}
    r = requests.get(OPENSKY_URL, params=params,
                     headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def decode_rows(data):
    """OpenSky 応答 → raw_positions 行のジェネレータ（逐次・低メモリ）。"""
    ts = data.get("time")
    for s in data.get("states") or []:
        if not s or s[0] is None:
            continue
        lon, lat = s[5], s[6]
        if lat is None or lon is None:
            continue
        callsign = (s[1] or "").strip() or None
        yield (
            s[0], callsign, s[2], lat, lon, s[7], s[9], s[10],
            1 if s[8] else 0, ts,
        )


def store_states(db, data):
    rows = list(decode_rows(data))
    if rows:
        db.executemany(
            "INSERT INTO raw_positions(icao24,callsign,origin_country,latitude,"
            "longitude,baro_altitude,velocity,true_track,on_ground,timestamp,"
            "collected_at) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))", rows)
        db.execute("INSERT INTO meta(key,value) VALUES('last_collect',"
                   "datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        db.commit()
    return len(rows)


def collect_once(db, bbox=None):
    last_exc = None
    for attempt in range(1, RETRIES + 1):
        try:
            data = fetch_states(bbox)
            return store_states(db, data)
        except Exception as e:   # noqa: BLE001 (収集ループは握り潰さず記録して継続)
            last_exc = e
            log.warning("fetch attempt %d/%d failed: %s", attempt, RETRIES, e)
            if attempt < RETRIES:
                time.sleep(RETRY_WAIT_SEC)
    log.error("collect failed after %d attempts: %s", RETRIES, last_exc)
    return 0


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bbox = None
    if os.environ.get("FT_BBOX"):
        bbox = [float(x) for x in os.environ["FT_BBOX"].split(",")]
    db = connect(DB_PATH)
    init_db(db)
    log.info("collector start: db=%s interval=%ss bbox=%s",
             DB_PATH, POLL_INTERVAL_SEC, bbox)
    while True:
        n = collect_once(db, bbox)
        log.info("stored %d positions", n)
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    sys.exit(main())
