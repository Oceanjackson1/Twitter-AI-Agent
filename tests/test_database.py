"""T2: Integration tests for database layer (db/)"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from db.database import Database
from db.ai_repo import AIRepo
from db.user_repo import UserRepo
from db.monitor_repo import MonitorRepo
from db.monitor_job_repo import MonitorJobRepo
from db.alert_repo import AlertRepo


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    await database.init()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def user_repo(db):
    return UserRepo(db)


@pytest_asyncio.fixture
async def monitor_repo(db):
    return MonitorRepo(db)


@pytest_asyncio.fixture
async def alert_repo(db):
    return AlertRepo(db)


@pytest_asyncio.fixture
async def ai_repo(db):
    return AIRepo(db)


@pytest_asyncio.fixture
async def monitor_job_repo(db):
    return MonitorJobRepo(db)


# === D1: Database init ===

@pytest.mark.asyncio
async def test_d1_tables_created(db):
    rows = await db.conn.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = {r["name"] for r in rows}
    assert "users" in table_names
    assert "monitors" in table_names
    assert "user_monitors" in table_names
    assert "alert_history" in table_names
    assert "monitor_jobs" in table_names
    assert "monitor_job_accounts" in table_names


# === D2-D5: UserRepo ===

@pytest.mark.asyncio
async def test_d2_create_new_user(user_repo):
    user = await user_repo.get_or_create(12345, "testuser")
    assert user.user_id == 12345
    assert user.username == "testuser"
    assert user.language == "zh"
    assert user.language_selected == 0

@pytest.mark.asyncio
async def test_d3_get_existing_user(user_repo):
    await user_repo.get_or_create(12345, "testuser")
    user = await user_repo.get_or_create(12345, "testuser")
    assert user.user_id == 12345

@pytest.mark.asyncio
async def test_d4_set_language(user_repo):
    await user_repo.get_or_create(12345)
    await user_repo.set_language(12345, "en")
    lang = await user_repo.get_language(12345)
    assert lang == "en"
    assert await user_repo.is_language_selected(12345) is True

@pytest.mark.asyncio
async def test_d5_update_settings(user_repo):
    await user_repo.get_or_create(12345)
    await user_repo.update_settings(12345, max_alerts=50, quiet_start="23:00", quiet_end="07:00")
    user = await user_repo.get_or_create(12345)
    assert user.max_alerts == 50
    assert user.quiet_start == "23:00"
    assert user.quiet_end == "07:00"


# === D6-D13: MonitorRepo ===

@pytest.mark.asyncio
async def test_d6_add_new_monitor(monitor_repo):
    monitor = await monitor_repo.add_monitor("ElonMusk")
    assert monitor.twitter_username == "elonmusk"
    assert monitor.is_active == 1

@pytest.mark.asyncio
async def test_d7_add_existing_monitor(monitor_repo):
    m1 = await monitor_repo.add_monitor("elonmusk")
    m2 = await monitor_repo.add_monitor("ElonMusk")
    assert m1.id == m2.id

@pytest.mark.asyncio
async def test_d8_subscribe(user_repo, monitor_repo):
    await user_repo.get_or_create(111)
    monitor = await monitor_repo.add_monitor("elonmusk")
    await monitor_repo.subscribe(111, monitor.id, "btc,crypto", delivery_type="webhook", delivery_target="https://example.com")

@pytest.mark.asyncio
async def test_d9_get_user_monitors(user_repo, monitor_repo):
    await user_repo.get_or_create(111)
    m1 = await monitor_repo.add_monitor("elonmusk")
    m2 = await monitor_repo.add_monitor("vitalikbuterin")
    await monitor_repo.subscribe(111, m1.id)
    await monitor_repo.subscribe(111, m2.id, "eth", delivery_type="group", delivery_target="-1001")
    monitors = await monitor_repo.get_user_monitors(111)
    assert len(monitors) == 2
    usernames = {m["twitter_username"] for m in monitors}
    assert "elonmusk" in usernames
    assert "vitalikbuterin" in usernames
    second = [m for m in monitors if m["twitter_username"] == "vitalikbuterin"][0]
    assert second["delivery_type"] == "group"
    assert second["delivery_target"] == "-1001"

@pytest.mark.asyncio
async def test_d10_unsubscribe_deactivates(user_repo, monitor_repo):
    await user_repo.get_or_create(111)
    monitor = await monitor_repo.add_monitor("elonmusk")
    await monitor_repo.subscribe(111, monitor.id)
    result = await monitor_repo.unsubscribe(111, "elonmusk")
    assert result is True
    active = await monitor_repo.get_all_active()
    assert len(active) == 0

@pytest.mark.asyncio
async def test_d10b_unsubscribe_nonexistent(monitor_repo):
    result = await monitor_repo.unsubscribe(999, "nonexistent")
    assert result is False

@pytest.mark.asyncio
async def test_d11_get_all_active(user_repo, monitor_repo):
    await user_repo.get_or_create(111)
    m1 = await monitor_repo.add_monitor("active_user")
    await monitor_repo.subscribe(111, m1.id)
    active = await monitor_repo.get_all_active()
    assert len(active) == 1
    assert active[0].twitter_username == "active_user"

@pytest.mark.asyncio
async def test_d12_update_last_seen(monitor_repo):
    monitor = await monitor_repo.add_monitor("testuser")
    await monitor_repo.update_last_seen(monitor.id, "999999")
    active = await monitor_repo.get_all_active()
    found = [m for m in active if m.id == monitor.id]
    assert found[0].last_seen_id == "999999"

@pytest.mark.asyncio
async def test_d13_get_subscribers(user_repo, monitor_repo):
    await user_repo.get_or_create(111)
    await user_repo.get_or_create(222)
    monitor = await monitor_repo.add_monitor("elonmusk")
    await monitor_repo.subscribe(111, monitor.id, "btc")
    await monitor_repo.subscribe(222, monitor.id, delivery_type="group", delivery_target="-100123")
    subs = await monitor_repo.get_subscribers("elonmusk")
    assert len(subs) == 2
    user_ids = {s["user_id"] for s in subs}
    assert 111 in user_ids
    assert 222 in user_ids
    group_sub = [s for s in subs if s["user_id"] == 222][0]
    assert group_sub["delivery_type"] == "group"


@pytest.mark.asyncio
async def test_d13b_create_monitor_job(user_repo, monitor_repo, monitor_job_repo):
    await user_repo.get_or_create(333)
    btc = await monitor_repo.add_monitor("btc_archive")
    eth = await monitor_repo.add_monitor("eth_archive")
    job = await monitor_job_repo.create_job(
        owner_user_id=333,
        delivery_type="telegram",
        delivery_target="333",
        output_mode="both",
        keywords="btc,etf",
    )
    await monitor_job_repo.add_account(job.id, btc.id)
    await monitor_job_repo.add_account(job.id, eth.id)

    jobs = await monitor_job_repo.get_user_jobs(333)
    assert len(jobs) == 1
    assert jobs[0]["account_count"] == 2
    assert jobs[0]["output_mode"] == "both"


# === D14-D15: AlertRepo ===

@pytest.mark.asyncio
async def test_d14_log_alert(user_repo, alert_repo):
    await user_repo.get_or_create(111)
    await alert_repo.log_alert(111, "elonmusk", "tweet123")

@pytest.mark.asyncio
async def test_d15_today_count(user_repo, alert_repo):
    await user_repo.get_or_create(111)
    await alert_repo.log_alert(111, "elonmusk", "tweet1")
    await alert_repo.log_alert(111, "elonmusk", "tweet2")
    await alert_repo.log_alert(111, "vitalik", "tweet3")
    count = await alert_repo.get_today_count(111)
    assert count == 3


@pytest.mark.asyncio
async def test_d16_ai_message_history(ai_repo, user_repo):
    await user_repo.get_or_create(111)
    await ai_repo.add_exchange(111, "Question 1", "Answer 1")
    await ai_repo.add_exchange(111, "Question 2", "Answer 2")
    history = await ai_repo.get_recent_messages(111, limit=3)
    assert len(history) == 3
    assert history[-1]["content"] == "Answer 2"
