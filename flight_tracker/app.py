# -*- coding: utf-8 -*-
"""app.py — Flask 照会API（読み取り専用）。nginx(127.0.0.1) 経由 + Cloudflare Tunnel。

エンドポイント:
  GET /api/routes?icao24=&callsign=&airport=&date=&limit=&offset=  ルート一覧(要約)
  GET /api/routes/<id>                                            ルート詳細(waypoints)
  GET /api/stats                                                  統計
  GET /healthz                                                    死活
出典: OpenSky Network / 空港: OurAirports (Public Domain)。
"""
import os
import json
import sqlite3

from flask import Flask, request, jsonify

DB_PATH = os.environ.get("FT_DB", "flight_tracker.db")
ATTRIBUTION = "Data: OpenSky Network. Airports: OurAirports (Public Domain)."
MAX_LIMIT = 200

app = Flask(__name__)


def _db():
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def _route_summary(row):
    return {
        "id": row["id"], "icao24": row["icao24"], "callsign": row["callsign"],
        "origin_country": row["origin_country"],
        "departure_time": row["departure_time"], "arrival_time": row["arrival_time"],
        "duration_minutes": row["duration_minutes"],
        "departure_airport": row["departure_airport"],
        "arrival_airport": row["arrival_airport"],
        "departure": [row["departure_lat"], row["departure_lon"]],
        "arrival": [row["arrival_lat"], row["arrival_lon"]],
        "max_altitude": row["max_altitude"], "avg_velocity": row["avg_velocity"],
    }


@app.get("/healthz")
def healthz():
    try:
        db = _db()
        n = db.execute("SELECT COUNT(*) c FROM flight_routes").fetchone()["c"]
        return jsonify(ok=True, routes=n, attribution=ATTRIBUTION)
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/routes")
def routes():
    icao24 = request.args.get("icao24")
    callsign = request.args.get("callsign")
    airport = request.args.get("airport")
    date = request.args.get("date")            # YYYY-MM-DD（出発日）
    try:
        limit = min(MAX_LIMIT, max(1, int(request.args.get("limit", "50"))))
        offset = max(0, int(request.args.get("offset", "0")))
    except ValueError:
        return jsonify(error="limit/offset must be integers"), 400

    where, params = [], []
    if icao24:
        where.append("icao24 = ?"); params.append(icao24.lower())
    if callsign:
        where.append("callsign = ?"); params.append(callsign.upper())
    if airport:
        a = airport.upper()
        where.append("(departure_airport = ? OR arrival_airport = ?)")
        params += [a, a]
    if date:
        where.append("substr(departure_time,1,10) = ?"); params.append(date)
    sql = "SELECT * FROM flight_routes"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY departure_time DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    db = _db()
    rows = db.execute(sql, params).fetchall()
    return jsonify(count=len(rows), limit=limit, offset=offset,
                   routes=[_route_summary(r) for r in rows],
                   attribution=ATTRIBUTION)


@app.get("/api/routes/<int:rid>")
def route_detail(rid):
    db = _db()
    row = db.execute("SELECT * FROM flight_routes WHERE id = ?", (rid,)).fetchone()
    if not row:
        return jsonify(error="not found"), 404
    out = _route_summary(row)
    out["waypoints"] = json.loads(row["waypoints"]) if row["waypoints"] else []
    out["attribution"] = ATTRIBUTION
    return jsonify(out)


@app.get("/api/stats")
def stats():
    db = _db()
    r = db.execute(
        "SELECT COUNT(*) routes, COUNT(DISTINCT icao24) aircraft, "
        "MIN(departure_time) first, MAX(arrival_time) last FROM flight_routes"
    ).fetchone()
    raw = db.execute("SELECT COUNT(*) c FROM raw_positions").fetchone()["c"]
    return jsonify(routes=r["routes"], aircraft=r["aircraft"],
                   first_departure=r["first"], last_arrival=r["last"],
                   raw_positions=raw, attribution=ATTRIBUTION)


if __name__ == "__main__":
    # 開発用。本番は gunicorn/waitress + systemd + nginx(127.0.0.1) で起動。
    app.run(host="127.0.0.1", port=int(os.environ.get("FT_PORT", "5002")))
