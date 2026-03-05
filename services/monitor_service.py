from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from telegram import Bot
from telegram.ext import CallbackContext

from db.database import Database
from db.user_repo import UserRepo
from db.monitor_repo import MonitorRepo
from db.monitor_job_repo import MonitorJobRepo
from db.alert_repo import AlertRepo
from services.csv_exporter import CSVExporter
from services.twitter_api import TwitterAPIClient
from utils.formatters import format_tweet_alert

logger = logging.getLogger(__name__)


class MonitorService:
    """Background task that polls Twitter accounts and dispatches alerts."""

    def __init__(
        self,
        twitter_api: TwitterAPIClient,
        db: Database,
        user_repo: UserRepo,
        monitor_repo: MonitorRepo,
        monitor_job_repo: MonitorJobRepo,
        alert_repo: AlertRepo,
        csv_exporter: CSVExporter,
        bot: Bot,
        poll_interval: int = 60,
    ):
        self.twitter_api = twitter_api
        self.db = db
        self.user_repo = user_repo
        self.monitor_repo = monitor_repo
        self.monitor_job_repo = monitor_job_repo
        self.alert_repo = alert_repo
        self.csv_exporter = csv_exporter
        self.bot = bot
        self.poll_interval = poll_interval

    def start(self, job_queue) -> None:
        """Register the repeating job with the application's JobQueue."""
        job_queue.run_repeating(
            callback=self.poll_all_monitors,
            interval=self.poll_interval,
            first=10,
            name="twitter_monitor_poll",
        )
        logger.info(f"Monitor service started (interval={self.poll_interval}s)")

    async def poll_all_monitors(self, context: CallbackContext) -> None:
        """Called by JobQueue every interval. Polls all active monitors."""
        monitors = await self.monitor_repo.get_all_active()
        if not monitors:
            return

        logger.info(f"Polling {len(monitors)} active monitors")
        for monitor in monitors:
            try:
                await self._check_account(monitor)
            except Exception as e:
                logger.error(f"Error checking @{monitor.twitter_username}: {e}")

    async def _check_account(self, monitor) -> None:
        """Check a single Twitter account for new tweets."""
        try:
            result = await self.twitter_api.get_user_tweets(
                username=monitor.twitter_username,
                max_results=10,
                include_replies=False,
                include_retweets=False,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch tweets for @{monitor.twitter_username}: {e}")
            return

        data = result.get("data") or result.get("tweets") or []
        if not data:
            return

        # Find new tweets (ID > last_seen_id) using numeric comparison
        last_seen_num = int(monitor.last_seen_id) if monitor.last_seen_id.isdigit() else 0
        if last_seen_num == 0:
            numeric_ids = [
                int(str(tweet.get("id", "0")))
                for tweet in data
                if str(tweet.get("id", "0")).isdigit()
            ]
            if numeric_ids:
                await self.monitor_repo.update_last_seen(monitor.id, str(max(numeric_ids)))
                logger.info(f"Initialized watermark for @{monitor.twitter_username} without replaying history")
            return

        new_tweets = []
        for tweet in data:
            tweet_id_str = str(tweet.get("id", "0"))
            tweet_id_num = int(tweet_id_str) if tweet_id_str.isdigit() else 0
            if tweet_id_num > last_seen_num:
                new_tweets.append(tweet)

        if not new_tweets:
            return

        # Update watermark (use numeric max)
        max_id = str(max(int(str(t.get("id", "0"))) for t in new_tweets if str(t.get("id", "0")).isdigit()))
        await self.monitor_repo.update_last_seen(monitor.id, max_id)

        jobs = await self.monitor_job_repo.get_jobs_for_monitor(monitor.id)
        if not jobs:
            return

        for tweet in new_tweets:
            for job in jobs:
                user_id = job["owner_user_id"]
                keywords = job.get("keywords")
                delivery_type = job.get("delivery_type") or "telegram"
                delivery_target = job.get("delivery_target")
                output_mode = job.get("output_mode") or "message"
                job_id = job["id"]

                # Apply keyword filter if configured
                if keywords:
                    keyword_list = [k.strip().lower() for k in keywords.split(",")]
                    tweet_text = (tweet.get("text") or "").lower()
                    if not any(kw in tweet_text for kw in keyword_list):
                        continue

                if output_mode in {"csv", "both"}:
                    self.csv_exporter.append_tweet(job_id, monitor.twitter_username, tweet)
                    if not job.get("csv_file_path"):
                        await self.monitor_job_repo.update_csv_file_path(
                            job_id,
                            self.csv_exporter.get_job_path(job_id),
                        )

                if output_mode == "csv":
                    continue

                # Check daily alert limit
                lang = await self.user_repo.get_language(user_id)
                user = await self.user_repo.get_or_create(user_id)
                today_count = await self.alert_repo.get_today_count(user_id)
                if today_count >= user.max_alerts:
                    continue

                # Check quiet hours
                if user.quiet_start and user.quiet_end:
                    now = datetime.now(timezone.utc)
                    current_time = now.strftime("%H:%M")
                    if user.quiet_start <= current_time or current_time < user.quiet_end:
                        if user.quiet_start > user.quiet_end:  # crosses midnight
                            continue

                # Send alert
                try:
                    message = format_tweet_alert(tweet, monitor.twitter_username, lang)
                    if delivery_type == "webhook":
                        await self._send_webhook_alert(
                            delivery_target,
                            monitor.twitter_username,
                            tweet,
                            message,
                            job_id,
                        )
                    else:
                        chat_id = user_id if delivery_type == "telegram" else int(delivery_target)
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            disable_web_page_preview=True,
                        )
                    await self.alert_repo.log_alert(
                        user_id, monitor.twitter_username, str(tweet.get("id", ""))
                    )
                    logger.info(
                        f"Alert sent via {delivery_type} for job {job_id} on @{monitor.twitter_username}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send alert to {user_id}: {e}")

    async def _send_webhook_alert(
        self,
        webhook_url: str | None,
        twitter_username: str,
        tweet: dict,
        formatted_message: str,
        job_id: int,
    ) -> None:
        if not webhook_url:
            raise ValueError("Webhook delivery selected without a webhook URL")

        payload = {
            "source": "twitter_monitor",
            "job_id": job_id,
            "twitter_username": twitter_username,
            "tweet": tweet,
            "message": formatted_message,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
