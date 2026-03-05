"""Unit tests for pagination token storage and keyboard payload size."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.callbacks.pagination import (
    build_page_keyboard,
    news_page_callback,
    register_pagination_params,
    resolve_pagination_params,
)


def test_pagination_token_keeps_callback_data_short():
    bot_data = {}
    token = register_pagination_params(bot_data, {
        "cmd": "search",
        "q": "polymarket",
        "title": "🔍 Search Results: polymarket",
    })

    keyboard = build_page_keyboard("news_page", 1, 25, token)
    callback_data = keyboard.inline_keyboard[0][-1].callback_data

    assert len(callback_data.encode("utf-8")) <= 64


def test_pagination_token_resolves_params():
    bot_data = {}
    params = {"cmd": "coin", "coin": "CARV", "title": "📰 News for CARV"}
    token = register_pagination_params(bot_data, params)

    assert resolve_pagination_params(bot_data, token) == params


def test_pagination_legacy_json_payload_still_resolves():
    bot_data = {}
    payload = '{"cmd":"news","title":"Latest"}'

    assert resolve_pagination_params(bot_data, payload) == {
        "cmd": "news",
        "title": "Latest",
    }


@pytest.mark.asyncio
async def test_news_page_callback_shows_progress_before_results():
    bot_data = {}
    token = register_pagination_params(bot_data, {
        "cmd": "search",
        "q": "polymarket",
        "title": "Search Results",
    })

    query = MagicMock()
    query.data = f"news_page:2:{token}"
    query.from_user.id = 123
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = MagicMock()
    query.message.edit_text = AsyncMock()

    update = MagicMock(callback_query=query)
    context = MagicMock()
    context.bot_data = {
        **bot_data,
        "user_repo": MagicMock(get_language=AsyncMock(return_value="en")),
        "news_api": MagicMock(
            search=AsyncMock(return_value={
                "data": [
                    {
                        "text": "Polymarket update",
                        "link": "https://example.com/1",
                        "newsType": "CoinDesk",
                        "engineType": "news",
                        "coins": [{"symbol": "POLY"}],
                    }
                ],
                "total": 6,
            })
        ),
    }

    await news_page_callback(update, context)

    first_edit = query.message.edit_text.await_args_list[0].args[0]
    final_edit = query.edit_message_text.await_args.args[0]
    assert "Processing request" in first_edit
    assert "Search Results" in final_edit
