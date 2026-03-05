from __future__ import annotations

import os
import aiosqlite
import logging

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    language    TEXT DEFAULT 'zh',
    language_selected INTEGER DEFAULT 0,
    max_alerts  INTEGER DEFAULT 100,
    quiet_start TEXT,
    quiet_end   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    twitter_username TEXT NOT NULL UNIQUE,
    last_seen_id     TEXT DEFAULT '0',
    is_active        INTEGER DEFAULT 1,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_monitors (
    user_id         INTEGER NOT NULL,
    monitor_id      INTEGER NOT NULL,
    keywords        TEXT,
    delivery_type   TEXT NOT NULL DEFAULT 'telegram',
    delivery_target TEXT,
    PRIMARY KEY (user_id, monitor_id)
);

CREATE TABLE IF NOT EXISTS alert_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    twitter_username TEXT NOT NULL,
    tweet_id         TEXT NOT NULL,
    sent_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    mode       TEXT DEFAULT 'ask',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitor_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id   INTEGER NOT NULL,
    delivery_type   TEXT NOT NULL DEFAULT 'telegram',
    delivery_target TEXT,
    output_mode     TEXT NOT NULL DEFAULT 'message',
    keywords        TEXT,
    is_active       INTEGER DEFAULT 1,
    csv_file_path   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitor_job_accounts (
    job_id      INTEGER NOT NULL,
    monitor_id  INTEGER NOT NULL,
    PRIMARY KEY (job_id, monitor_id)
);

CREATE INDEX IF NOT EXISTS idx_monitors_username ON monitors(twitter_username);
CREATE INDEX IF NOT EXISTS idx_user_monitors_user ON user_monitors(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_user_date ON alert_history(user_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_ai_messages_user_id ON ai_messages(user_id, id);
CREATE INDEX IF NOT EXISTS idx_monitor_jobs_owner ON monitor_jobs(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_monitor_job_accounts_monitor ON monitor_job_accounts(monitor_id);
"""


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._run_migrations()
        await self._conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    async def _run_migrations(self):
        assert self._conn is not None

        if await self._add_column_if_missing("users", "language_selected", "INTEGER DEFAULT 0"):
            # Existing users already have a usable language preference; only new users should be prompted.
            await self._conn.execute("UPDATE users SET language_selected = 1")

        await self._add_column_if_missing(
            "user_monitors",
            "delivery_type",
            "TEXT NOT NULL DEFAULT 'telegram'",
        )
        await self._add_column_if_missing("user_monitors", "delivery_target", "TEXT")

        await self._conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_messages (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id    INTEGER NOT NULL,
                   role       TEXT NOT NULL,
                   content    TEXT NOT NULL,
                   mode       TEXT DEFAULT 'ask',
                   created_at TEXT DEFAULT (datetime('now'))
               )"""
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_messages_user_id ON ai_messages(user_id, id)"
        )
        await self._conn.execute(
            """CREATE TABLE IF NOT EXISTS monitor_jobs (
                   id              INTEGER PRIMARY KEY AUTOINCREMENT,
                   owner_user_id   INTEGER NOT NULL,
                   delivery_type   TEXT NOT NULL DEFAULT 'telegram',
                   delivery_target TEXT,
                   output_mode     TEXT NOT NULL DEFAULT 'message',
                   keywords        TEXT,
                   is_active       INTEGER DEFAULT 1,
                   csv_file_path   TEXT,
                   created_at      TEXT DEFAULT (datetime('now'))
               )"""
        )
        await self._conn.execute(
            """CREATE TABLE IF NOT EXISTS monitor_job_accounts (
                   job_id      INTEGER NOT NULL,
                   monitor_id  INTEGER NOT NULL,
                   PRIMARY KEY (job_id, monitor_id)
               )"""
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitor_jobs_owner ON monitor_jobs(owner_user_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitor_job_accounts_monitor ON monitor_job_accounts(monitor_id)"
        )
        await self._migrate_legacy_user_monitors()

    async def _migrate_legacy_user_monitors(self):
        assert self._conn is not None
        existing_jobs = await self._conn.execute_fetchall(
            "SELECT COUNT(*) AS cnt FROM monitor_jobs"
        )
        if existing_jobs[0]["cnt"] > 0:
            return

        legacy_rows = await self._conn.execute_fetchall(
            """SELECT um.user_id, um.keywords, um.delivery_type, um.delivery_target, m.id AS monitor_id
               FROM user_monitors um
               JOIN monitors m ON um.monitor_id = m.id"""
        )
        for row in legacy_rows:
            cursor = await self._conn.execute(
                """INSERT INTO monitor_jobs
                   (owner_user_id, delivery_type, delivery_target, output_mode, keywords)
                   VALUES (?, ?, ?, 'message', ?)""",
                (
                    row["user_id"],
                    row["delivery_type"] or "telegram",
                    row["delivery_target"],
                    row["keywords"],
                ),
            )
            job_id = cursor.lastrowid
            await self._conn.execute(
                "INSERT OR IGNORE INTO monitor_job_accounts (job_id, monitor_id) VALUES (?, ?)",
                (job_id, row["monitor_id"]),
            )

    async def _add_column_if_missing(self, table: str, column: str, definition: str) -> bool:
        assert self._conn is not None
        rows = await self._conn.execute_fetchall(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in rows}
        if column in columns:
            return False
        await self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return True

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn is not None, "Database not initialized"
        return self._conn

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
