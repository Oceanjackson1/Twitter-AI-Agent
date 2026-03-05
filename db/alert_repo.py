from db.database import Database


class AlertRepo:
    def __init__(self, db: Database):
        self.db = db

    async def log_alert(self, user_id: int, twitter_username: str, tweet_id: str):
        await self.db.conn.execute(
            "INSERT INTO alert_history (user_id, twitter_username, tweet_id) VALUES (?, ?, ?)",
            (user_id, twitter_username, tweet_id),
        )
        await self.db.conn.commit()

    async def get_today_count(self, user_id: int) -> int:
        rows = await self.db.conn.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM alert_history WHERE user_id = ? AND date(sent_at) = date('now')",
            (user_id,),
        )
        return rows[0]["cnt"] if rows else 0
