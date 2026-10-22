import sqlite3
from contextlib import contextmanager

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content TEXT NOT NULL,
  short TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'You',
  category TEXT NOT NULL,
  zone TEXT NOT NULL,
  rule TEXT NOT NULL,
  sensitivity TEXT NOT NULL,
  status TEXT NOT NULL,
  decision_reason TEXT,
  session_id TEXT,
  expires_at TEXT,
  source_text TEXT,
  created_at TEXT NOT NULL,
  last_used_at TEXT,
  use_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS deletion_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_id INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  category TEXT NOT NULL,
  rule TEXT NOT NULL,
  zone TEXT NOT NULL,
  reason TEXT NOT NULL,
  deleted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  zone TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ask_answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  choice TEXT NOT NULL,
  zone TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learned_prefs (
  category TEXT PRIMARY KEY,
  behavior TEXT NOT NULL,
  zone TEXT,
  source TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS connections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  zone TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  last_used_at TEXT
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  connection_id INTEGER,
  app TEXT NOT NULL,
  action TEXT NOT NULL,
  memory_ids TEXT NOT NULL DEFAULT '[]',
  count INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_access (
  memory_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  PRIMARY KEY (memory_id, connection_id)
);
CREATE INDEX IF NOT EXISTS memories_status_zone ON memories(status, zone);
CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id);
"""


def connect():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    memory_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(memories)")
    }
    if "source" not in memory_columns:
        connection.execute(
            "ALTER TABLE memories ADD COLUMN source TEXT NOT NULL DEFAULT 'You'"
        )
        connection.execute(
            "UPDATE memories SET source = 'Sample data' "
            "WHERE decision_reason = 'Seeded demo memory'"
        )
    if "shared" not in memory_columns:
        # 1 = connected AI apps may use it, 0 = only this app's own chat.
        connection.execute(
            "ALTER TABLE memories ADD COLUMN shared INTEGER NOT NULL DEFAULT 1"
        )
    if "visibility" not in {
        row["name"] for row in connection.execute("PRAGMA table_info(memories)")
    }:
        # open = every connected AI, sensitive = no AI, custom = only chosen AIs
        connection.execute(
            "ALTER TABLE memories ADD COLUMN visibility TEXT NOT NULL DEFAULT 'open'"
        )
        connection.execute(
            "UPDATE memories SET visibility = CASE WHEN shared = 1 AND sensitivity != 'high' "
            "THEN 'open' ELSE 'sensitive' END"
        )
    connection_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(connections)")
    }
    if "last_used_at" not in connection_columns:
        connection.execute("ALTER TABLE connections ADD COLUMN last_used_at TEXT")
    if "zones" not in connection_columns:
        connection.execute("ALTER TABLE connections ADD COLUMN zones TEXT")
        connection.execute("UPDATE connections SET zones = zone")
    if "can_write" not in connection_columns:
        connection.execute(
            "ALTER TABLE connections ADD COLUMN can_write INTEGER NOT NULL DEFAULT 1"
        )
    return connection


@contextmanager
def get_db():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
