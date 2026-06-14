# -*- coding: utf-8 -*-
"""SQLite 初期化・接続（Flight Tracker）。

raw_positions: 一時データ（OpenSky の全機スナップショットを蓄積、2-3日で削除）
flight_routes: 永久保存（着陸検出でフライト単位のルートを生成）

軽量運用（共用2GB VPS）のため WAL + NORMAL。書き込みはバッチINSERT。
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_positions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  icao24        TEXT    NOT NULL,
  callsign      TEXT,
  origin_country TEXT,
  latitude      REAL,
  longitude     REAL,
  baro_altitude REAL,
  velocity      REAL,
  true_track    REAL,
  on_ground     INTEGER,            -- 0/1
  timestamp     INTEGER NOT NULL,   -- OpenSky の UNIX 秒
  collected_at  TEXT    NOT NULL    -- 収集日時(UTC ISO)
);
CREATE INDEX IF NOT EXISTS idx_raw_icao24    ON raw_positions(icao24);
CREATE INDEX IF NOT EXISTS idx_raw_timestamp ON raw_positions(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_collected ON raw_positions(collected_at);

CREATE TABLE IF NOT EXISTS flight_routes (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  icao24           TEXT NOT NULL,
  callsign         TEXT,
  origin_country   TEXT,
  departure_time   TEXT,            -- UTC ISO
  arrival_time     TEXT,
  duration_minutes INTEGER,
  departure_lat    REAL,
  departure_lon    REAL,
  arrival_lat      REAL,
  arrival_lon      REAL,
  departure_airport TEXT,           -- ICAO(推定)
  arrival_airport   TEXT,
  waypoints        TEXT,            -- JSON [[lat,lon,alt,ts],...]（間引き済み）
  max_altitude     REAL,
  avg_velocity     REAL,
  created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_route_icao24      ON flight_routes(icao24);
CREATE INDEX IF NOT EXISTS idx_route_callsign    ON flight_routes(callsign);
CREATE INDEX IF NOT EXISTS idx_route_departure   ON flight_routes(departure_time);
CREATE INDEX IF NOT EXISTS idx_route_arr_airport ON flight_routes(arrival_airport);
CREATE INDEX IF NOT EXISTS idx_route_dep_airport ON flight_routes(departure_airport);

-- collector の進捗・最終取得時刻などのメタ
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=10000")
    return db


def init_db(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMA)
    db.commit()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "flight_tracker.db"
    db = connect(path)
    init_db(db)
    print(f"initialized {path}")
