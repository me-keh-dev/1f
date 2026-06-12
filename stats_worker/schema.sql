CREATE TABLE IF NOT EXISTS votes (
  uid TEXT NOT NULL,
  scene TEXT NOT NULL,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
  PRIMARY KEY (uid, scene)
);
CREATE INDEX IF NOT EXISTS idx_votes_scene ON votes (scene);

-- 同意の上で送信される匿名エラーログ
CREATE TABLE IF NOT EXISTS errlogs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  ver TEXT,
  skeleton TEXT,
  platform TEXT,
  os TEXT,
  log TEXT
);
