"""T4: Bot command handler tests using mocks."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import config
from db.ai_repo import AIRepo
from db.database import Database
from db.user_repo import UserRepo
from db.monitor_repo import MonitorRepo
from db.monitor_job_repo import MonitorJobRepo
from db.alert_repo import AlertRepo
from services.news_api import NewsAPIClient
from services.twitter_api import TwitterAPIClient
from services.deepseek import DeepseekClient
from services.csv_exporter import CSVExporter


def make_update_and_context(user_id=12345, username="testuser", args=None, chat_id=12345, chat_type="private"):
    """Create mock Telegram Update and Context objects."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_chat.id = chat_id
    update.effective_chat.type = chat_type
    update.effective_chat.send_action = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.args = args or []
    context.bot_data = {}
    return update, context


@pytest_asyncio.fixture
async def services(tmp_path):
    """Set up real DB + real API clients for command testing."""
    db = Database(str(tmp_path / "test.db"))
    await db.init()

    user_repo = UserRepo(db)
    monitor_repo = MonitorRepo(db)
    monitor_job_repo = MonitorJobRepo(db)
    alert_repo = AlertRepo(db)
    ai_repo = AIRepo(db)
    news_api = NewsAPIClient(config.OPENNEWS_API_BASE, config.OPENNEWS_TOKEN)
    twitter_api = TwitterAPIClient(config.TWITTER_API_BASE, config.TWITTER_TOKEN)
    deepseek = DeepseekClient(config.DEEPSEEK_API_KEY, config.DEEPSEEK_API_BASE)
    csv_exporter = CSVExporter(base_dir=str(tmp_path / "exports"))

    yield {
        "db": db,
        "user_repo": user_repo,
        "monitor_repo": monitor_repo,
        "monitor_job_repo": monitor_job_repo,
        "alert_repo": alert_repo,
        "ai_repo": ai_repo,
        "news_api": news_api,
        "twitter_api": twitter_api,
        "deepseek": deepseek,
        "csv_exporter": csv_exporter,
    }

    await news_api.close()
    await twitter_api.close()
    await deepseek.close()
    await db.close()


def inject_services(context, services):
    context.bot_data.update(services)


# === B1: /start ===

@pytest.mark.asyncio
async def test_b1_start_new_user(services):
    from bot.commands.start import start_command

    update, context = make_update_and_context(user_id=99999, username="newguy")
    inject_services(context, services)

    await start_command(update, context)

    update.message.reply_text.assert_called_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "选择语言" in reply_text or "Choose your language" in reply_text
    assert update.message.reply_text.call_args.kwargs["reply_markup"] is not None

    # Verify user was created in DB
    user = await services["user_repo"].get_or_create(99999)
    assert user.user_id == 99999


@pytest.mark.asyncio
async def test_b1b_start_existing_user_shows_welcome(services):
    from bot.commands.start import start_command

    await services["user_repo"].get_or_create(12345, "testuser")
    await services["user_repo"].set_language(12345, "en", selected=True)

    update, context = make_update_and_context()
    inject_services(context, services)

    await start_command(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "CryptoEye Agent" in reply_text
    assert "/news" in reply_text


# === B2: /help ===

@pytest.mark.asyncio
async def test_b2_help(services):
    from bot.commands.start import help_command

    update, context = make_update_and_context()
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await help_command(update, context)

    update.message.reply_text.assert_called_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "/news" in reply_text
    assert "/monitor" in reply_text
    assert "/ask" in reply_text


# === B3: /lang ===

@pytest.mark.asyncio
async def test_b3_lang(services):
    from bot.commands.start import lang_command

    update, context = make_update_and_context()
    inject_services(context, services)

    await lang_command(update, context)

    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args
    # Should have reply_markup (inline keyboard)
    assert call_kwargs.kwargs.get("reply_markup") or (len(call_kwargs) > 1 and call_kwargs[1])


# === B4: /news ===

@pytest.mark.asyncio
async def test_b4_news(services):
    from bot.commands.news import news_command

    update, context = make_update_and_context()
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await news_command(update, context)

    assert update.message.reply_text.called
    first_reply = update.message.reply_text.call_args_list[0].args[0]
    reply_text = update.message.reply_text.call_args[0][0]
    assert "处理中" in first_reply or "Processing request" in first_reply
    assert len(reply_text) > 10  # Should have some content


# === B5: /search_news no args ===

@pytest.mark.asyncio
async def test_b5_search_news_no_args(services):
    from bot.commands.news import search_news_command

    update, context = make_update_and_context(args=[])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await search_news_command(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "/search_news" in reply_text  # Usage hint


# === B6: /coin_news BTC ===

@pytest.mark.asyncio
async def test_b6_coin_news_btc(services):
    from bot.commands.news import coin_news_command

    update, context = make_update_and_context(args=["BTC"])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await coin_news_command(update, context)

    assert update.message.reply_text.called


@pytest.mark.asyncio
async def test_b6b_news_keyword_search_uses_short_pagination_token():
    from bot.commands.news import news_command

    update, context = make_update_and_context(args=["polymarket"])
    context.bot_data = {
        "user_repo": MagicMock(get_language=AsyncMock(return_value="en")),
        "news_api": MagicMock(
            search=AsyncMock(return_value={
                "data": [
                    {
                        "text": f"Polymarket article {i}",
                        "link": f"https://example.com/{i}",
                        "newsType": "CoinDesk",
                        "engineType": "news",
                        "coins": [{"symbol": "POLY"}],
                    }
                    for i in range(5)
                ],
                "total": 12,
            }),
            get_latest=AsyncMock(),
        ),
    }

    await news_command(update, context)

    context.bot_data["news_api"].search.assert_awaited_once_with("polymarket", limit=5, page=1)
    context.bot_data["news_api"].get_latest.assert_not_called()

    reply_text = update.message.reply_text.call_args[0][0]
    reply_markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    callback_data = reply_markup.inline_keyboard[0][-1].callback_data

    assert "Search Results: polymarket" in reply_text
    assert len(callback_data.encode("utf-8")) <= 64


# === B7: /tw_user no args ===

@pytest.mark.asyncio
async def test_b7_tw_user_no_args(services):
    from bot.commands.twitter import tw_user_command

    update, context = make_update_and_context(args=[])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await tw_user_command(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "/tw_user" in reply_text


# === B8: /tw_user elonmusk ===

@pytest.mark.asyncio
async def test_b8_tw_user_elonmusk(services):
    from bot.commands.twitter import tw_user_command

    update, context = make_update_and_context(args=["elonmusk"])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await tw_user_command(update, context)

    assert update.message.reply_text.called
    first_reply = update.message.reply_text.call_args_list[0].args[0]
    reply_text = update.message.reply_text.call_args[0][0]
    assert "处理中" in first_reply or "Processing request" in first_reply
    assert "elonmusk" in reply_text.lower() or "elon" in reply_text.lower()


# === B9: /monitor elonmusk ===

@pytest.mark.asyncio
async def test_b9_monitor_add(services):
    from bot.commands.monitor import monitor_command, PENDING_MONITOR_KEY

    update, context = make_update_and_context(args=["elonmusk", "vitalikbuterin"])
    inject_services(context, services)

    await monitor_command(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "进度" in reply_text or "Progress" in reply_text
    assert "elonmusk" in reply_text
    assert update.message.reply_text.call_args.kwargs["reply_markup"] is not None
    assert 12345 in context.bot_data[PENDING_MONITOR_KEY]

    jobs = await services["monitor_job_repo"].get_user_jobs(12345)
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_b9b_monitor_delivery_dm_finalizes_subscription(services):
    from bot.commands.monitor import monitor_command
    from bot.callbacks.inline_handlers import monitor_delivery_callback, monitor_output_callback

    update, context = make_update_and_context(args=["elonmusk", "vitalikbuterin"])
    inject_services(context, services)
    await monitor_command(update, context)

    callback_update = MagicMock()
    callback_update.callback_query = MagicMock()
    callback_update.callback_query.data = "monitor_delivery:telegram"
    callback_update.callback_query.from_user.id = 12345
    callback_update.callback_query.answer = AsyncMock()
    callback_update.callback_query.edit_message_text = AsyncMock()
    callback_update.callback_query.message.chat.id = 12345

    await monitor_delivery_callback(callback_update, context)

    output_update = MagicMock()
    output_update.callback_query = MagicMock()
    output_update.callback_query.data = "monitor_output:message"
    output_update.callback_query.from_user.id = 12345
    output_update.callback_query.answer = AsyncMock()
    output_update.callback_query.edit_message_text = AsyncMock()
    output_update.callback_query.message.chat.id = 12345
    await monitor_output_callback(output_update, context)

    assert context.bot_data["pending_input_requests"][12345]["kind"] == "monitor_keywords_text"


@pytest.mark.asyncio
async def test_b9c_monitor_keywords_added_in_dialog(services):
    from bot.commands.monitor import monitor_command, pending_input_message_handler
    from bot.callbacks.inline_handlers import monitor_delivery_callback, monitor_output_callback

    update, context = make_update_and_context(args=["elonmusk", "vitalikbuterin"])
    inject_services(context, services)
    await monitor_command(update, context)

    callback_update = MagicMock()
    callback_update.callback_query = MagicMock()
    callback_update.callback_query.data = "monitor_delivery:telegram"
    callback_update.callback_query.from_user.id = 12345
    callback_update.callback_query.answer = AsyncMock()
    callback_update.callback_query.edit_message_text = AsyncMock()
    callback_update.callback_query.message.chat.id = 12345
    await monitor_delivery_callback(callback_update, context)

    output_update = MagicMock()
    output_update.callback_query = MagicMock()
    output_update.callback_query.data = "monitor_output:both"
    output_update.callback_query.from_user.id = 12345
    output_update.callback_query.answer = AsyncMock()
    output_update.callback_query.edit_message_text = AsyncMock()
    output_update.callback_query.message.chat.id = 12345
    await monitor_output_callback(output_update, context)

    update2, context2 = make_update_and_context(args=None)
    update2.message.text = "btc, etf"
    inject_services(context2, services)
    context2.bot_data.update(context.bot_data)

    await pending_input_message_handler(update2, context2)

    jobs = await services["monitor_job_repo"].get_user_jobs(12345)
    assert len(jobs) == 1
    assert jobs[0]["keywords"] == "btc, etf"
    assert jobs[0]["output_mode"] == "both"


# === B10: /monitors ===

@pytest.mark.asyncio
async def test_b10_monitors_list(services):
    from bot.commands.monitor import monitor_command, monitors_command
    from bot.callbacks.inline_handlers import monitor_delivery_callback, monitor_output_callback, monitor_keywords_callback

    update, context = make_update_and_context(args=["testaccount"])
    inject_services(context, services)
    await monitor_command(update, context)

    callback_update = MagicMock()
    callback_update.callback_query = MagicMock()
    callback_update.callback_query.data = "monitor_delivery:telegram"
    callback_update.callback_query.from_user.id = 12345
    callback_update.callback_query.answer = AsyncMock()
    callback_update.callback_query.edit_message_text = AsyncMock()
    callback_update.callback_query.message.chat.id = 12345
    await monitor_delivery_callback(callback_update, context)

    output_update = MagicMock()
    output_update.callback_query = MagicMock()
    output_update.callback_query.data = "monitor_output:csv"
    output_update.callback_query.from_user.id = 12345
    output_update.callback_query.answer = AsyncMock()
    output_update.callback_query.edit_message_text = AsyncMock()
    output_update.callback_query.message.chat.id = 12345
    await monitor_output_callback(output_update, context)

    keyword_update = MagicMock()
    keyword_update.callback_query = MagicMock()
    keyword_update.callback_query.data = "monitor_keywords:skip"
    keyword_update.callback_query.from_user.id = 12345
    keyword_update.callback_query.answer = AsyncMock()
    keyword_update.callback_query.edit_message_text = AsyncMock()
    keyword_update.callback_query.message.reply_text = AsyncMock()
    await monitor_keywords_callback(keyword_update, context)

    update2, context2 = make_update_and_context()
    inject_services(context2, services)
    await monitors_command(update2, context2)

    reply_text = update2.message.reply_text.call_args[0][0]
    assert "testaccount" in reply_text
    assert "Job #" in reply_text or "任务 #" in reply_text


# === B11: /unmonitor ===

@pytest.mark.asyncio
async def test_b11_unmonitor(services):
    from bot.commands.monitor import monitor_command, unmonitor_command
    from bot.callbacks.inline_handlers import monitor_delivery_callback, monitor_output_callback, monitor_keywords_callback

    # First add
    update, context = make_update_and_context(args=["removeuser"])
    inject_services(context, services)
    await monitor_command(update, context)

    callback_update = MagicMock()
    callback_update.callback_query = MagicMock()
    callback_update.callback_query.data = "monitor_delivery:telegram"
    callback_update.callback_query.from_user.id = 12345
    callback_update.callback_query.answer = AsyncMock()
    callback_update.callback_query.edit_message_text = AsyncMock()
    callback_update.callback_query.message.chat.id = 12345
    await monitor_delivery_callback(callback_update, context)

    output_update = MagicMock()
    output_update.callback_query = MagicMock()
    output_update.callback_query.data = "monitor_output:message"
    output_update.callback_query.from_user.id = 12345
    output_update.callback_query.answer = AsyncMock()
    output_update.callback_query.edit_message_text = AsyncMock()
    output_update.callback_query.message.chat.id = 12345
    await monitor_output_callback(output_update, context)

    keyword_update = MagicMock()
    keyword_update.callback_query = MagicMock()
    keyword_update.callback_query.data = "monitor_keywords:skip"
    keyword_update.callback_query.from_user.id = 12345
    keyword_update.callback_query.answer = AsyncMock()
    keyword_update.callback_query.edit_message_text = AsyncMock()
    keyword_update.callback_query.message.reply_text = AsyncMock()
    await monitor_keywords_callback(keyword_update, context)

    # Then remove
    jobs = await services["monitor_job_repo"].get_user_jobs(12345)
    update2, context2 = make_update_and_context(args=[str(jobs[0]["id"])])
    inject_services(context2, services)
    await unmonitor_command(update2, context2)

    reply_text = update2.message.reply_text.call_args[0][0]
    assert "removed" in reply_text.lower() or "已删除" in reply_text


@pytest.mark.asyncio
async def test_b11b_export_csv(services):
    from bot.commands.monitor import monitor_command, export_csv_command
    from bot.callbacks.inline_handlers import monitor_delivery_callback, monitor_output_callback, monitor_keywords_callback

    update, context = make_update_and_context(args=["csvuser"])
    update.message.reply_document = AsyncMock()
    inject_services(context, services)
    await monitor_command(update, context)

    delivery_update = MagicMock()
    delivery_update.callback_query = MagicMock()
    delivery_update.callback_query.data = "monitor_delivery:telegram"
    delivery_update.callback_query.from_user.id = 12345
    delivery_update.callback_query.answer = AsyncMock()
    delivery_update.callback_query.edit_message_text = AsyncMock()
    delivery_update.callback_query.message.chat.id = 12345
    await monitor_delivery_callback(delivery_update, context)

    output_update = MagicMock()
    output_update.callback_query = MagicMock()
    output_update.callback_query.data = "monitor_output:csv"
    output_update.callback_query.from_user.id = 12345
    output_update.callback_query.answer = AsyncMock()
    output_update.callback_query.edit_message_text = AsyncMock()
    output_update.callback_query.message.chat.id = 12345
    await monitor_output_callback(output_update, context)

    keyword_update = MagicMock()
    keyword_update.callback_query = MagicMock()
    keyword_update.callback_query.data = "monitor_keywords:skip"
    keyword_update.callback_query.from_user.id = 12345
    keyword_update.callback_query.answer = AsyncMock()
    keyword_update.callback_query.edit_message_text = AsyncMock()
    keyword_update.callback_query.message.reply_text = AsyncMock()
    await monitor_keywords_callback(keyword_update, context)

    jobs = await services["monitor_job_repo"].get_user_jobs(12345)

    export_update, export_context = make_update_and_context(args=[str(jobs[0]["id"])])
    export_update.message.reply_document = AsyncMock()
    inject_services(export_context, services)

    await export_csv_command(export_update, export_context)

    export_update.message.reply_document.assert_called_once()


# === B12: /ask no args ===

@pytest.mark.asyncio
async def test_b12_ask_no_args(services):
    from bot.commands.ai import ask_command

    update, context = make_update_and_context(args=[])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await ask_command(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "/ask" in reply_text


# === B13: /ask with question ===

@pytest.mark.asyncio
async def test_b13_ask_with_question(services):
    from bot.commands.ai import ask_command

    update, context = make_update_and_context(args=["what", "is", "bitcoin"])
    inject_services(context, services)
    await services["user_repo"].get_or_create(12345)

    await ask_command(update, context)

    # Should have been called at least twice (loading + answer)
    assert update.message.reply_text.call_count >= 2


@pytest.mark.asyncio
async def test_b13b_ask_uses_ai_memory_history():
    from bot.commands.ai import ask_command

    update, context = make_update_and_context(args=["follow", "up", "question"])
    context.bot_data = {
        "user_repo": MagicMock(get_language=AsyncMock(return_value="en")),
        "deepseek": MagicMock(chat_messages=AsyncMock(return_value="Answer")),
        "ai_repo": MagicMock(
            get_recent_messages=AsyncMock(return_value=[
                {"role": "user", "content": "Earlier question"},
                {"role": "assistant", "content": "Earlier answer"},
            ]),
            add_exchange=AsyncMock(),
        ),
    }

    await ask_command(update, context)

    messages = context.bot_data["deepseek"].chat_messages.call_args.args[0]
    assert messages[1]["content"] == "Earlier question"
    assert messages[2]["content"] == "Earlier answer"
    context.bot_data["ai_repo"].add_exchange.assert_awaited_once()
