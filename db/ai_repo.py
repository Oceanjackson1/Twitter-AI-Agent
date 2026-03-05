from __future__ import annotations

from db.database import Database


class AIRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_recent_messages(self, user_id: int, limit: int = 8) -> list[dict]:
        rows = await self.db.conn.execute_fetchall(
            """SELECT role, content
               FROM ai_messages
               WHERE user_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (user_id, limit),
        )
        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    async def add_message(self, user_id: int, role: str, content: str, mode: str = "ask"):
        await self.db.conn.execute(
            "INSERT INTO ai_messages (user_id, role, content, mode) VALUES (?, ?, ?, ?)",
            (user_id, role, content[:4000], mode),
        )
        await self.db.conn.commit()

    async def add_exchange(
        self,
        user_id: int,
        user_message: str,
        assistant_message: str,
        mode: str = "ask",
    ):
        await self.add_message(user_id, "user", user_message, mode=mode)
        await self.add_message(user_id, "assistant", assistant_message, mode=mode)
        await self.prune_history(user_id)

    async def prune_history(self, user_id: int, keep_last: int = 20):
        await self.db.conn.execute(
            """DELETE FROM ai_messages
               WHERE user_id = ?
                 AND id NOT IN (
                     SELECT id
                     FROM ai_messages
                     WHERE user_id = ?
                     ORDER BY id DESC
                     LIMIT ?
                 )""",
            (user_id, user_id, keep_last),
        )
        await self.db.conn.commit()
