# -*- coding: utf-8 -*-
"""cleanup — 古い raw_positions を削除し VACUUM（日次 cron）。
flight_routes は永久保存（削除しない）。raw は ephemeral（既定3日）。
"""
import os
import logging

from db import connect, init_db

RETENTION_DAYS = int(os.environ.get("FT_RAW_RETENTION_DAYS", "3"))
DB_PATH = os.environ.get("FT_DB", "flight_tracker.db")

log = logging.getLogger("cleanup")


def cleanup(db, retention_days=RETENTION_DAYS):
    cur = db.execute(
        "DELETE FROM raw_positions WHERE collected_at < datetime('now', ?)",
        (f"-{retention_days} days",))
    deleted = cur.rowcount
    db.commit()
    db.execute("VACUUM")          # SQLite 容量回収
    return deleted


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = connect(DB_PATH)
    init_db(db)
    n = cleanup(db)
    log.info("deleted %d old raw positions; vacuumed", n)


if __name__ == "__main__":
    main()
