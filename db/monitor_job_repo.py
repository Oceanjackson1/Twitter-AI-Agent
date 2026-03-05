from __future__ import annotations

from db.database import Database
from db.models import MonitorJob


class MonitorJobRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create_job(
        self,
        owner_user_id: int,
        delivery_type: str,
        delivery_target: str | None,
        output_mode: str,
        keywords: str | None = None,
        csv_file_path: str | None = None,
    ) -> MonitorJob:
        cursor = await self.db.conn.execute(
            """INSERT INTO monitor_jobs
               (owner_user_id, delivery_type, delivery_target, output_mode, keywords, csv_file_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                owner_user_id,
                delivery_type,
                delivery_target,
                output_mode,
                keywords,
                csv_file_path,
            ),
        )
        await self.db.conn.commit()
        return MonitorJob(
            id=cursor.lastrowid,
            owner_user_id=owner_user_id,
            delivery_type=delivery_type,
            delivery_target=delivery_target,
            output_mode=output_mode,
            keywords=keywords,
            csv_file_path=csv_file_path,
        )

    async def add_account(self, job_id: int, monitor_id: int):
        await self.db.conn.execute(
            "INSERT OR IGNORE INTO monitor_job_accounts (job_id, monitor_id) VALUES (?, ?)",
            (job_id, monitor_id),
        )
        await self.db.conn.commit()

    async def update_keywords(self, job_id: int, keywords: str | None):
        await self.db.conn.execute(
            "UPDATE monitor_jobs SET keywords = ? WHERE id = ?",
            (keywords, job_id),
        )
        await self.db.conn.commit()

    async def update_csv_file_path(self, job_id: int, csv_file_path: str):
        await self.db.conn.execute(
            "UPDATE monitor_jobs SET csv_file_path = ? WHERE id = ?",
            (csv_file_path, job_id),
        )
        await self.db.conn.commit()

    async def get_job(self, job_id: int, owner_user_id: int | None = None) -> dict | None:
        params: list[object] = [job_id]
        query = """SELECT j.*,
                          GROUP_CONCAT(m.twitter_username, ',') AS accounts
                   FROM monitor_jobs j
                   LEFT JOIN monitor_job_accounts ja ON ja.job_id = j.id
                   LEFT JOIN monitors m ON m.id = ja.monitor_id
                   WHERE j.id = ?"""
        if owner_user_id is not None:
            query += " AND j.owner_user_id = ?"
            params.append(owner_user_id)
        query += " GROUP BY j.id"
        rows = await self.db.conn.execute_fetchall(query, tuple(params))
        if not rows:
            return None
        row = dict(rows[0])
        row["accounts"] = row["accounts"].split(",") if row.get("accounts") else []
        return row

    async def get_user_jobs(self, owner_user_id: int) -> list[dict]:
        rows = await self.db.conn.execute_fetchall(
            """SELECT j.*,
                      COUNT(ja.monitor_id) AS account_count,
                      GROUP_CONCAT(m.twitter_username, ', ') AS accounts
               FROM monitor_jobs j
               LEFT JOIN monitor_job_accounts ja ON ja.job_id = j.id
               LEFT JOIN monitors m ON m.id = ja.monitor_id
               WHERE j.owner_user_id = ? AND j.is_active = 1
               GROUP BY j.id
               ORDER BY j.id DESC""",
            (owner_user_id,),
        )
        return [dict(row) for row in rows]

    async def get_jobs_for_monitor(self, monitor_id: int) -> list[dict]:
        rows = await self.db.conn.execute_fetchall(
            """SELECT j.*
               FROM monitor_jobs j
               JOIN monitor_job_accounts ja ON ja.job_id = j.id
               WHERE ja.monitor_id = ? AND j.is_active = 1""",
            (monitor_id,),
        )
        return [dict(row) for row in rows]

    async def delete_job(self, owner_user_id: int, job_id: int) -> list[int]:
        rows = await self.db.conn.execute_fetchall(
            "SELECT id FROM monitor_jobs WHERE id = ? AND owner_user_id = ?",
            (job_id, owner_user_id),
        )
        if not rows:
            return []

        rows = await self.db.conn.execute_fetchall(
            "SELECT monitor_id FROM monitor_job_accounts WHERE job_id = ?",
            (job_id,),
        )
        monitor_ids = [row["monitor_id"] for row in rows]
        await self.db.conn.execute(
            "DELETE FROM monitor_job_accounts WHERE job_id = ?",
            (job_id,),
        )
        cursor = await self.db.conn.execute(
            "DELETE FROM monitor_jobs WHERE id = ? AND owner_user_id = ?",
            (job_id, owner_user_id),
        )
        await self.db.conn.commit()
        if cursor.rowcount == 0:
            return []
        return monitor_ids

    async def find_single_account_jobs(self, owner_user_id: int, username: str) -> list[dict]:
        rows = await self.db.conn.execute_fetchall(
            """SELECT j.id
               FROM monitor_jobs j
               JOIN monitor_job_accounts ja ON ja.job_id = j.id
               JOIN monitors m ON m.id = ja.monitor_id
               WHERE j.owner_user_id = ?
                 AND j.is_active = 1
                 AND m.twitter_username = ?
               GROUP BY j.id
               HAVING COUNT(ja.monitor_id) = 1""",
            (owner_user_id, username.lower()),
        )
        return [dict(row) for row in rows]

    async def count_jobs_for_monitor(self, monitor_id: int) -> int:
        rows = await self.db.conn.execute_fetchall(
            """SELECT COUNT(*) AS cnt
               FROM monitor_job_accounts ja
               JOIN monitor_jobs j ON j.id = ja.job_id
               WHERE ja.monitor_id = ? AND j.is_active = 1""",
            (monitor_id,),
        )
        return rows[0]["cnt"] if rows else 0
