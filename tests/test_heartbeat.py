"""T6: Heartbeat reporting tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock

import pytest

import config
from bot.application import create_application, error_handler, post_shutdown
from services.heartbeat import PixelOfficeHeartbeat


@pytest.mark.asyncio
async def test_h1_heartbeat_posts_expected_payload():
    heartbeat = PixelOfficeHeartbeat(
        endpoint="https://example.com/rest/v1/agents",
        api_key="token",
        agent_id="cryptoeye-agent-main",
        name="CryptoEye Agent",
        role="lead",
        role_label_zh="加密情报总控",
        enabled=True,
    )
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=response)
    heartbeat._get_client = AsyncMock(return_value=client)

    await heartbeat.report("working", "Serving Telegram updates and monitor jobs")

    client.post.assert_awaited_once()
    call = client.post.await_args
    assert call.args[0] == "https://example.com/rest/v1/agents"
    assert call.kwargs["json"]["id"] == "cryptoeye-agent-main"
    assert call.kwargs["json"]["name"] == "CryptoEye Agent"
    assert call.kwargs["json"]["status"] == "working"


@pytest.mark.asyncio
async def test_h2_heartbeat_skips_duplicate_state():
    heartbeat = PixelOfficeHeartbeat(
        endpoint="https://example.com/rest/v1/agents",
        api_key="token",
        agent_id="cryptoeye-agent-main",
        name="CryptoEye Agent",
        role="lead",
        role_label_zh="加密情报总控",
        enabled=True,
    )
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=response)
    heartbeat._get_client = AsyncMock(return_value=client)

    await heartbeat.report_online()
    await heartbeat.report_online()

    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_h3_error_handler_reports_exception_and_recovers():
    heartbeat = MagicMock()
    heartbeat.report_exception = AsyncMock()
    heartbeat.report_online = AsyncMock()

    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.error = RuntimeError("boom")
    context.application.bot_data = {"heartbeat": heartbeat}

    await error_handler(update, context)

    heartbeat.report_exception.assert_awaited_once()
    heartbeat.report_online.assert_awaited_once()
    update.effective_message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_h4_post_shutdown_reports_sleeping_and_closes():
    heartbeat = MagicMock()
    heartbeat.report_stopped = AsyncMock()
    heartbeat.close = AsyncMock()

    application = MagicMock()
    application.bot_data = {
        "heartbeat": heartbeat,
        "db": MagicMock(close=AsyncMock()),
        "news_api": MagicMock(close=AsyncMock()),
        "twitter_api": MagicMock(close=AsyncMock()),
        "deepseek": MagicMock(close=AsyncMock()),
    }

    await post_shutdown(application)

    heartbeat.report_stopped.assert_awaited_once()
    heartbeat.close.assert_awaited_once()


def test_h5_create_application_registers_heartbeat():
    app = create_application()
    heartbeat = app.bot_data["heartbeat"]

    assert isinstance(heartbeat, PixelOfficeHeartbeat)
    assert heartbeat.agent_id == config.PIXEL_OFFICE_AGENT_ID
