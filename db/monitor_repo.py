from __future__ import annotations

from db.database import Database
from db.models import Monitor, UserMonitor


class MonitorRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add_monitor(self, twitter_username: str) -> Monitor:
        """Add a Twitter account to the monitors table (or get existing)."""
        row = await self.db.conn.execute_fetchall(
            "SELECT * FROM monitors WHERE twitter_username = ?",
            (twitter_username.lower(),),
        )
        if row:
            r = row[0]
            if not r["is_active"]:
                await self.db.conn.execute(
                    "UPDATE monitors SET is_active = 1 WHERE id = ?",
                    (r["id"],),
                )
                await self.db.conn.commit()
                r = dict(r)
                r["is_active"] = 1
            return Monitor(
                id=r["id"],
                twitter_username=r["twitter_username"],
                last_seen_id=r["last_seen_id"],
                is_active=r["is_active"],
                created_at=r["created_at"],
            )
        cursor = await self.db.conn.execute(
            "INSERT INTO monitors (twitter_username) VALUES (?)",
            (twitter_username.lower(),),
        )
        await self.db.conn.commit()
        return Monitor(id=cursor.lastrowid, twitter_username=twitter_username.lower())

    async def subscribe(
        self,
        user_id: int,
        monitor_id: int,
        keywords: str | None = None,
        delivery_type: str = "telegram",
        delivery_target: str | None = None,
    ):
        """Subscribe a user to a monitor."""
        await self.db.conn.execute(
            """INSERT OR REPLACE INTO user_monitors
               (user_id, monitor_id, keywords, delivery_type, delivery_target)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, monitor_id, keywords, delivery_type, delivery_target),
        )
        await self.db.conn.commit()

    async def unsubscribe(self, user_id: int, twitter_username: str) -> bool:
        """Unsubscribe user from a monitor. Returns True if removed."""
        row = await self.db.conn.execute_fetchall(
            "SELECT id FROM monitors WHERE twitter_username = ?",
            (twitter_username.lower(),),
        )
        if not row:
            return False
        monitor_id = row[0]["id"]
        cursor = await self.db.conn.execute(
            "DELETE FROM user_monitors WHERE user_id = ? AND monitor_id = ?",
            (user_id, monitor_id),
        )
        await self.db.conn.commit()
        # If no subscribers left, deactivate monitor
        subs = await self.db.conn.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM user_monitors WHERE monitor_id = ?",
            (monitor_id,),
        )
        if subs[0]["cnt"] == 0:
            await self.db.conn.execute(
                "UPDATE monitors SET is_active = 0 WHERE id = ?", (monitor_id,)
            )
            await self.db.conn.commit()
        return cursor.rowcount > 0

    async def update_subscription_keywords(
        self,
        user_id: int,
        twitter_username: str,
        keywords: str | None,
    ):
        await self.db.conn.execute(
            """UPDATE user_monitors
               SET keywords = ?
               WHERE user_id = ?
                 AND monitor_id = (
                     SELECT id FROM monitors WHERE twitter_username = ?
                 )""",
            (keywords, user_id, twitter_username.lower()),
        )
        await self.db.conn.commit()

    async def get_user_monitors(self, user_id: int) -> list[dict]:
        """Get all monitors a user is subscribed to."""
        rows = await self.db.conn.execute_fetchall(
            """SELECT m.twitter_username, um.keywords, um.delivery_type, um.delivery_target, m.is_active
               FROM user_monitors um
               JOIN monitors m ON um.monitor_id = m.id
               WHERE um.user_id = ?""",
            (user_id,),
        )
        return [dict(r) for r in rows]

    async def get_all_active(self) -> list[Monitor]:
        """Get all active monitors (for polling)."""
        rows = await self.db.conn.execute_fetchall(
            "SELECT * FROM monitors WHERE is_active = 1"
        )
        return [
            Monitor(
                id=r["id"],
                twitter_username=r["twitter_username"],
                last_seen_id=r["last_seen_id"],
                is_active=r["is_active"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def update_last_seen(self, monitor_id: int, last_seen_id: str):
        await self.db.conn.execute(
            "UPDATE monitors SET last_seen_id = ? WHERE id = ?",
            (last_seen_id, monitor_id),
        )
        await self.db.conn.commit()

    async def set_active(self, monitor_id: int, is_active: int):
        await self.db.conn.execute(
            "UPDATE monitors SET is_active = ? WHERE id = ?",
            (is_active, monitor_id),
        )
        await self.db.conn.commit()

    async def get_subscribers(self, twitter_username: str) -> list[dict]:
        """Get all users subscribed to a given Twitter username with their keywords."""
        rows = await self.db.conn.execute_fetchall(
            """SELECT um.user_id, um.keywords, um.delivery_type, um.delivery_target
               FROM user_monitors um
               JOIN monitors m ON um.monitor_id = m.id
               WHERE m.twitter_username = ?""",
            (twitter_username.lower(),),
        )
        return [dict(r) for r in rows]
