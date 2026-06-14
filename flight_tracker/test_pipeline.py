# -*- coding: utf-8 -*-
"""ローカル検証: route_generator + cleanup + Flask API（ネットワーク不要・合成データ）。
  python test_pipeline.py    （airports.csv が必要: python fetch_airports.py）
"""
import os
import time
import json
import tempfile

DBP = tempfile.mktemp(suffix=".db")
os.environ["FT_DB"] = DBP

import db as DB        # noqa: E402
import airports as ap  # noqa: E402
import route_generator as rg  # noqa: E402
import cleanup as cl   # noqa: E402

fails = []


def ok(cond, msg):
    print(("  ok: " if cond else "  FAIL: ") + msg)
    if not cond:
        fails.append(msg)


conn = DB.connect(DBP)
DB.init_db(conn)
aps = ap.load_airports("airports.csv")
now = int(time.time())


def _sqlfmt(unix):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix))


def ins(icao, cs, lat, lon, alt, og, ts, collected=None):
    ca = collected if collected else _sqlfmt(now)
    conn.execute(
        "INSERT INTO raw_positions(icao24,callsign,origin_country,latitude,"
        "longitude,baro_altitude,velocity,true_track,on_ground,timestamp,"
        "collected_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (icao, cs, "Japan", lat, lon, alt, 420, 90, og, ts, ca))


# 完了フライト: 羽田->成田、40分前に着陸
t0 = now - 90 * 60
N = 12
for i in range(N):
    f = i / (N - 1)
    og = 1 if i in (0, N - 1) else 0
    ins("abc001", "ANA001", 35.553 + 0.212 * f, 139.781 + 0.605 * f,
        0 if og else 9000, og, int(t0 + f * 50 * 60))
# 進行中（生成しない）
ins("abc002", "JAL002", 40.0, 140.0, 10000, 0, now - 5 * 60)
conn.commit()

print("[route_generator]")
made = rg.generate(conn, aps, now=now)
ok(made == 1, f"one completed flight generated (got {made})")
row = conn.execute(
    "SELECT departure_airport,arrival_airport,duration_minutes,waypoints "
    "FROM flight_routes").fetchone()
ok(row[0] == "RJTT" and row[1] == "RJAA", f"airports RJTT->RJAA (got {row[0]}->{row[1]})")
ok(row[2] == 50, f"duration 50min (got {row[2]})")
ok(len(json.loads(row[3])) == 12, "waypoints preserved")
ok(conn.execute("SELECT COUNT(*) FROM raw_positions WHERE icao24='abc001'")
   .fetchone()[0] == 0, "completed flight raw deleted")
ok(conn.execute("SELECT COUNT(*) FROM raw_positions WHERE icao24='abc002'")
   .fetchone()[0] == 1, "in-progress flight raw kept")

print("[cleanup]")
ins("old001", "X", 1, 1, 1000, 0, now - 10 * 86400,
    collected=_sqlfmt(now - 5 * 86400))
conn.commit()
deleted = cl.cleanup(conn, retention_days=3)
ok(deleted == 1, f"old raw deleted (got {deleted})")

print("[Flask API]")
conn.close()
import app as flask_app  # noqa: E402  (FT_DB は上で設定済み)
c = flask_app.app.test_client()
ok(c.get("/healthz").get_json()["ok"] is True, "/healthz ok")
j = c.get("/api/routes?icao24=abc001").get_json()
ok(j["count"] == 1 and j["routes"][0]["arrival_airport"] == "RJAA",
   "/api/routes?icao24 returns the flight")
ok(c.get("/api/routes?airport=RJTT").get_json()["count"] == 1,
   "/api/routes?airport=RJTT matches departure")
rid = j["routes"][0]["id"]
d = c.get(f"/api/routes/{rid}").get_json()
ok("waypoints" in d and len(d["waypoints"]) == 12, "/api/routes/<id> has waypoints")
ok(c.get("/api/routes/99999").status_code == 404, "unknown route -> 404")
s = c.get("/api/stats").get_json()
ok(s["routes"] == 1 and s["aircraft"] == 1, "/api/stats counts")

print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED")
raise SystemExit(1 if fails else 0)
