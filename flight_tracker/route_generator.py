# -*- coding: utf-8 -*-
"""route_generator — raw_positions から「完了したフライト」を検出して flight_routes に保存。

アルゴリズム（軽量・低メモリ・冪等）:
  1) raw_positions の icao24 を1つずつ処理。
  2) その機体の位置列を時刻順に取得し、連続収集の隙間 > LANDING_GAP_SEC（既定30分）
     でフライト区間に分割。
  3) 各区間のうち「完了」したもの（後ろに別区間がある or 末尾が now-30分より古い＝
     レーダーから消失＝着陸とみなす）だけ flight_routes 化する。
  4) 出発/到着は on_ground 点を優先して推定し、最寄り空港（OurAirports）にスナップ。
  5) waypoints は間引いて JSON 保存。処理済みの raw 行は削除（ephemeral）。
     まだ進行中の最終区間は残す（次回処理）。
"""
import os
import json
import time
import logging

from db import connect, init_db
import airports as ap

LANDING_GAP_SEC = int(os.environ.get("FT_LANDING_GAP_SEC", str(30 * 60)))
MIN_FLIGHT_MINUTES = int(os.environ.get("FT_MIN_FLIGHT_MIN", "5"))
MIN_POINTS = int(os.environ.get("FT_MIN_POINTS", "3"))
MAX_WAYPOINTS = int(os.environ.get("FT_MAX_WAYPOINTS", "120"))
AIRPORT_MATCH_KM = float(os.environ.get("FT_AIRPORT_KM", "15"))
DB_PATH = os.environ.get("FT_DB", "flight_tracker.db")
AIRPORTS_CSV = os.environ.get("FT_AIRPORTS_CSV", "airports.csv")

log = logging.getLogger("route_gen")


def _split_flights(rows):
    """rows=[(ts, lat, lon, alt, vel, track, on_ground, callsign, country)] 時刻順。
    隙間でフライトに分割して返す。"""
    flights, cur = [], []
    for r in rows:
        if cur and (r[0] - cur[-1][0]) > LANDING_GAP_SEC:
            flights.append(cur)
            cur = []
        cur.append(r)
    if cur:
        flights.append(cur)
    return flights


def _decimate(points, maxn):
    """[[lat,lon,alt,ts],...] を maxn 以下に間引く（端点保持・等間隔）。"""
    n = len(points)
    if n <= maxn:
        return points
    step = n / maxn
    out = [points[int(i * step)] for i in range(maxn)]
    out[-1] = points[-1]
    return out


def _endpoint(seg, at_start):
    """出発/到着点を推定。on_ground 点があれば優先。"""
    ground = [r for r in seg if r[6]]
    if ground:
        return ground[0] if at_start else ground[-1]
    return seg[0] if at_start else seg[-1]


def _make_route(icao24, seg, airports, now):
    dep = _endpoint(seg, True)
    arr = _endpoint(seg, False)
    dur_min = int((arr[0] - dep[0]) / 60)
    if dur_min < MIN_FLIGHT_MINUTES or len(seg) < MIN_POINTS:
        return None
    callsign = next((r[7] for r in seg if r[7]), None)
    country = seg[0][8]
    alts = [r[3] for r in seg if r[3] is not None]
    vels = [r[4] for r in seg if r[4] is not None]
    wpts = _decimate([[r[1], r[2], r[3], r[0]] for r in seg], MAX_WAYPOINTS)
    dep_ap, _ = ap.nearest_airport(dep[1], dep[2], airports, AIRPORT_MATCH_KM)
    arr_ap, _ = ap.nearest_airport(arr[1], arr[2], airports, AIRPORT_MATCH_KM)
    return (
        icao24, callsign, country,
        _iso(dep[0]), _iso(arr[0]), dur_min,
        dep[1], dep[2], arr[1], arr[2],
        dep_ap, arr_ap, json.dumps(wpts, separators=(",", ":")),
        max(alts) if alts else None,
        round(sum(vels) / len(vels), 1) if vels else None,
    )


def _iso(unix_sec):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(unix_sec))


def generate(db, airports, now=None):
    """完了フライトを flight_routes へ。生成数を返す。"""
    now = now if now is not None else int(time.time())
    icaos = [r[0] for r in db.execute(
        "SELECT DISTINCT icao24 FROM raw_positions").fetchall()]
    made = 0
    for icao in icaos:
        rows = db.execute(
            "SELECT timestamp,latitude,longitude,baro_altitude,velocity,"
            "true_track,on_ground,callsign,origin_country FROM raw_positions "
            "WHERE icao24=? ORDER BY timestamp", (icao,)).fetchall()
        if not rows:
            continue
        flights = _split_flights(rows)
        # 最終区間が進行中（末尾が new）の場合は残し、それ以外を処理
        last_in_progress = (flights and
                            (now - flights[-1][-1][0]) <= LANDING_GAP_SEC)
        completed = flights[:-1] if last_in_progress else flights
        keep_from_ts = flights[-1][0][0] if last_in_progress else None
        for seg in completed:
            route = _make_route(icao, seg, airports, now)
            if route:
                db.execute(
                    "INSERT INTO flight_routes(icao24,callsign,origin_country,"
                    "departure_time,arrival_time,duration_minutes,departure_lat,"
                    "departure_lon,arrival_lat,arrival_lon,departure_airport,"
                    "arrival_airport,waypoints,max_altitude,avg_velocity,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))", route)
                made += 1
        # 処理済み raw を削除（進行中区間は残す）
        if keep_from_ts is not None:
            db.execute("DELETE FROM raw_positions WHERE icao24=? AND timestamp<?",
                       (icao, keep_from_ts))
        else:
            db.execute("DELETE FROM raw_positions WHERE icao24=?", (icao,))
    db.commit()
    return made


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    airports = ap.load_airports(AIRPORTS_CSV)
    db = connect(DB_PATH)
    init_db(db)
    made = generate(db, airports)
    log.info("generated %d routes", made)


if __name__ == "__main__":
    main()
