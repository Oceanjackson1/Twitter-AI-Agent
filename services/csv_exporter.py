from __future__ import annotations

import csv
import os
from datetime import datetime, timezone


class CSVExporter:
    def __init__(self, base_dir: str = "data/exports"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def get_job_path(self, job_id: int) -> str:
        return os.path.join(self.base_dir, f"monitor_job_{job_id}.csv")

    def ensure_file(self, job_id: int) -> str:
        path = self.get_job_path(job_id)
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "account",
                    "tweet_id",
                    "tweet_created_at",
                    "captured_at",
                    "text",
                    "tweet_url",
                    "retweets",
                    "likes",
                    "replies",
                    "quotes",
                ])
        return path

    def append_tweet(self, job_id: int, account: str, tweet: dict) -> str:
        path = self.ensure_file(job_id)
        tweet_id = str(tweet.get("id", ""))
        author = tweet.get("userScreenName") or tweet.get("screenName") or account
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                account,
                tweet_id,
                tweet.get("createdAt", tweet.get("created_at", "")),
                datetime.now(timezone.utc).isoformat(),
                (tweet.get("text") or "").replace("\r\n", "\n").replace("\r", "\n"),
                f"https://x.com/{author}/status/{tweet_id}" if author and tweet_id else "",
                tweet.get("retweetCount", 0),
                tweet.get("favoriteCount", tweet.get("likeCount", 0)),
                tweet.get("replyCount", 0),
                tweet.get("quoteCount", 0),
            ])
        return path
