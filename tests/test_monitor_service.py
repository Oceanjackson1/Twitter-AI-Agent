"""T5: Monitor service tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from db.database import Database
from db.user_repo import UserRepo
from db.monitor_repo import MonitorRepo
from db.monitor_job_repo import MonitorJobRepo
from db.alert_repo import AlertRepo
from services.csv_exporter import CSVExporter
from services.monitor_service import MonitorService


@pytest_asyncio.fixture
async def setup(tmp_path):
    """Set up test database and mock services."""
    db = Database(str(tmp_path / "test.db"))
    await db.init()

    user_repo = UserRepo(db)
    monitor_repo = MonitorRepo(db)
    monitor_job_repo = MonitorJobRepo(db)
    alert_repo = AlertRepo(db)
    csv_exporter = CSVExporter(base_dir=str(tmp_path / "exports"))

    # Mock twitter API
    twitter_api = AsyncMock()
    bot = AsyncMock()

    service = MonitorService(
        twitter_api=twitter_api,
        db=db,
        user_repo=user_repo,
        monitor_repo=monitor_repo,
        monitor_job_repo=monitor_job_repo,
        alert_repo=alert_repo,
        csv_exporter=csv_exporter,
        bot=bot,
        poll_interval=60,
    )

    yield {
        "db": db,
        "user_repo": user_repo,
        "monitor_repo": monitor_repo,
        "monitor_job_repo": monitor_job_repo,
        "alert_repo": alert_repo,
        "csv_exporter": csv_exporter,
        "twitter_api": twitter_api,
        "bot": bot,
        "service": service,
    }

    await db.close()


# === M1: No active monitors ===

@pytest.mark.asyncio
async def test_m1_no_active_monitors(setup):
    """poll_all_monitors should not error when no monitors exist."""
    service = setup["service"]
    context = MagicMock()

    await service.poll_all_monitors(context)
    # Should complete without error
    setup["twitter_api"].get_user_tweets.assert_not_called()


# === M2: No new tweets ===

@pytest.mark.asyncio
async def test_m2_no_new_tweets(setup):
    """When all tweets have ID <= last_seen_id, no alerts should be sent."""
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]

    # Setup: user + monitor with last_seen_id = "100"
    await user_repo.get_or_create(111, "user1")
    monitor = await monitor_repo.add_monitor("testuser")
    job = await monitor_job_repo.create_job(111, "telegram", "111", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "100")

    # Mock: return tweets all with ID <= 100
    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "99", "text": "old tweet 1"},
            {"id": "100", "text": "old tweet 2"},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    # No alerts should be sent
    setup["bot"].send_message.assert_not_called()


@pytest.mark.asyncio
async def test_m2b_first_poll_sets_watermark_without_replaying_history(setup):
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]

    await user_repo.get_or_create(111, "user1")
    monitor = await monitor_repo.add_monitor("freshuser")
    job = await monitor_job_repo.create_job(111, "telegram", "111", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "105", "text": "Recent tweet"},
            {"id": "104", "text": "Older tweet"},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    setup["bot"].send_message.assert_not_called()
    active = await monitor_repo.get_all_active()
    updated = [m for m in active if m.twitter_username == "freshuser"]
    assert updated[0].last_seen_id == "105"


# === M3: New tweets trigger alerts ===

@pytest.mark.asyncio
async def test_m3_new_tweets_trigger_alert(setup):
    """New tweets (ID > last_seen_id) should trigger alert to subscribers."""
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    bot = setup["bot"]

    # Setup
    await user_repo.get_or_create(111, "user1")
    monitor = await monitor_repo.add_monitor("testuser")
    job = await monitor_job_repo.create_job(111, "telegram", "111", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "100")

    # Mock: return tweets with one new (ID > 100)
    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "101", "text": "New exciting tweet about BTC!", "retweetCount": 10, "favoriteCount": 50, "replyCount": 5, "createdAt": "2026-02-28"},
            {"id": "99", "text": "old tweet"},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    # Alert should be sent
    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args
    assert call_kwargs.kwargs["chat_id"] == 111
    assert "New exciting tweet" in call_kwargs.kwargs["text"]

    # last_seen_id should be updated
    active = await monitor_repo.get_all_active()
    updated = [m for m in active if m.twitter_username == "testuser"]
    assert updated[0].last_seen_id == "101"


# === M4: Keyword filtering ===

@pytest.mark.asyncio
async def test_m4_keyword_filter(setup):
    """Tweets not matching keywords should not trigger alerts."""
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    bot = setup["bot"]

    await user_repo.get_or_create(111, "user1")
    monitor = await monitor_repo.add_monitor("testuser")
    job = await monitor_job_repo.create_job(111, "telegram", "111", "message", keywords="bitcoin,btc")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "100")

    # Tweet about ETH, not BTC
    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "101", "text": "Ethereum is the future of DeFi!", "retweetCount": 0, "favoriteCount": 0, "replyCount": 0},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    # Should NOT send alert (ETH tweet doesn't match btc/bitcoin keywords)
    bot.send_message.assert_not_called()


# === M4b: Keyword match triggers alert ===

@pytest.mark.asyncio
async def test_m4b_keyword_match(setup):
    """Tweets matching keywords should trigger alerts."""
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    bot = setup["bot"]

    await user_repo.get_or_create(222, "user2")
    monitor = await monitor_repo.add_monitor("testuser2")
    job = await monitor_job_repo.create_job(222, "telegram", "222", "message", keywords="bitcoin")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "200")

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "201", "text": "Bitcoin hits new ATH!", "retweetCount": 100, "favoriteCount": 500, "replyCount": 20, "createdAt": "2026-02-28"},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_m4c_group_delivery_uses_group_chat_id(setup):
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    bot = setup["bot"]

    await user_repo.get_or_create(333, "groupowner")
    monitor = await monitor_repo.add_monitor("groupuser")
    job = await monitor_job_repo.create_job(333, "group", "-100555", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "10")

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "11", "text": "Group delivery tweet", "retweetCount": 1, "favoriteCount": 2, "replyCount": 3},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    bot.send_message.assert_called_once()
    assert bot.send_message.call_args.kwargs["chat_id"] == -100555


@pytest.mark.asyncio
async def test_m4d_webhook_delivery_calls_webhook(setup):
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]

    await user_repo.get_or_create(444, "webhookowner")
    monitor = await monitor_repo.add_monitor("webhookuser")
    job = await monitor_job_repo.create_job(444, "webhook", "https://example.com/webhook", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "20")

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "21", "text": "Webhook delivery tweet", "retweetCount": 1, "favoriteCount": 2, "replyCount": 3},
        ]
    }

    service._send_webhook_alert = AsyncMock()

    context = MagicMock()
    await service.poll_all_monitors(context)

    service._send_webhook_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_m4e_csv_output_appends_rows(setup):
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    csv_exporter = setup["csv_exporter"]

    await user_repo.get_or_create(555, "csvowner")
    monitor = await monitor_repo.add_monitor("csvuser")
    job = await monitor_job_repo.create_job(555, "telegram", "555", "csv")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "300")

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "301", "text": "CSV line", "retweetCount": 1, "favoriteCount": 2, "replyCount": 3, "createdAt": "2026-02-28"},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    path = csv_exporter.get_job_path(job.id)
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    assert "csvuser" in data
    assert "CSV line" in data


# === M5: Daily alert limit ===

@pytest.mark.asyncio
async def test_m5_daily_alert_limit(setup):
    """When user exceeds max_alerts, no more alerts should be sent."""
    user_repo = setup["user_repo"]
    monitor_repo = setup["monitor_repo"]
    monitor_job_repo = setup["monitor_job_repo"]
    alert_repo = setup["alert_repo"]
    twitter_api = setup["twitter_api"]
    service = setup["service"]
    bot = setup["bot"]

    await user_repo.get_or_create(111, "user1")
    await user_repo.update_settings(111, max_alerts=2)

    monitor = await monitor_repo.add_monitor("busyuser")
    job = await monitor_job_repo.create_job(111, "telegram", "111", "message")
    await monitor_job_repo.add_account(job.id, monitor.id)
    await monitor_repo.update_last_seen(monitor.id, "100")

    # Pre-fill 2 alerts (already at limit)
    await alert_repo.log_alert(111, "busyuser", "prev1")
    await alert_repo.log_alert(111, "busyuser", "prev2")

    twitter_api.get_user_tweets.return_value = {
        "data": [
            {"id": "101", "text": "New tweet", "retweetCount": 0, "favoriteCount": 0, "replyCount": 0},
        ]
    }

    context = MagicMock()
    await service.poll_all_monitors(context)

    # Should NOT send alert (at daily limit)
    bot.send_message.assert_not_called()
