from __future__ import annotations

from db.database import Database
from db.models import User


class UserRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_or_create(self, user_id: int, username: str | None = None) -> User:
        row = await self.db.conn.execute_fetchall(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        if row:
            r = row[0]
            if username and username != r["username"]:
                await self.db.conn.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (username, user_id),
                )
                await self.db.conn.commit()
            return User(
                user_id=r["user_id"],
                username=r["username"],
                language=r["language"],
                language_selected=r["language_selected"],
                max_alerts=r["max_alerts"],
                quiet_start=r["quiet_start"],
                quiet_end=r["quiet_end"],
                created_at=r["created_at"],
            )
        await self.db.conn.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await self.db.conn.commit()
        return User(user_id=user_id, username=username)

    async def get_language(self, user_id: int) -> str:
        row = await self.db.conn.execute_fetchall(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        )
        if row:
            return row[0]["language"]
        return "zh"

    async def set_language(self, user_id: int, language: str, selected: bool = True):
        await self.db.conn.execute(
            """INSERT INTO users (user_id, language, language_selected)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   language = excluded.language,
                   language_selected = excluded.language_selected""",
            (user_id, language, 1 if selected else 0),
        )
        await self.db.conn.commit()

    async def is_language_selected(self, user_id: int) -> bool:
        row = await self.db.conn.execute_fetchall(
            "SELECT language_selected FROM users WHERE user_id = ?",
            (user_id,),
        )
        if not row:
            return False
        return bool(row[0]["language_selected"])

    async def update_settings(self, user_id: int, **kwargs):
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        await self.db.conn.execute(
            f"UPDATE users SET {sets} WHERE user_id = ?", vals
        )
        await self.db.conn.commit()
