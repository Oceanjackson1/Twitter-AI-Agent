import logging
from telegram import Update
from telegram.ext import ContextTypes

from i18n.translator import get_text
from utils.formatters import format_news_article, split_long_message
from utils.progress import ProgressMessage
from utils.validators import validate_coin_symbol, validate_signal
from bot.callbacks.pagination import (
    build_page_keyboard,
    register_pagination_params,
    ITEMS_PER_PAGE,
)

logger = logging.getLogger(__name__)


async def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_repo = context.bot_data["user_repo"]
    return await user_repo.get_language(update.effective_user.id)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/news [count|keyword] - Get latest crypto news or search by keyword."""
    lang = await _get_lang(update, context)
    news_api = context.bot_data["news_api"]

    count = ITEMS_PER_PAGE
    title = get_text("news_title", lang)
    params = {"cmd": "news", "title": title}

    if context.args:
        try:
            count = min(int(context.args[0]), 20)
        except ValueError:
            keyword = " ".join(context.args).strip()
            if keyword:
                progress = await ProgressMessage.start(
                    update.message.reply_text,
                    lang,
                    get_text("progress_task_fetching_news", lang),
                    percent=20,
                )
                try:
                    result = await news_api.search(keyword, limit=ITEMS_PER_PAGE, page=1)
                except Exception as e:
                    logger.error(f"News search error: {e}")
                    await progress.fail(get_text("progress_task_failed", lang))
                    await update.message.reply_text(get_text("error_api", lang))
                    return

                articles = (result.get("data") or []) if result else []
                if not articles:
                    await progress.complete(get_text("progress_task_no_results", lang))
                    await update.message.reply_text(get_text("news_no_results", lang))
                    return

                total = result.get("total", len(articles))
                total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                title = get_text("news_search_title", lang, keyword=keyword)
                params = {"cmd": "search", "q": keyword, "title": title}
                await progress.update(80, get_text("progress_task_formatting", lang))

                lines = [title + "\n"]
                for article in articles:
                    lines.append(format_news_article(article, lang))
                    lines.append("")

                token = register_pagination_params(context.bot_data, params)
                keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None

                for chunk in split_long_message("\n".join(lines)):
                    await update.message.reply_text(
                        chunk, reply_markup=keyboard, disable_web_page_preview=True
                    )
                    keyboard = None
                await progress.complete(get_text("progress_task_result_ready", lang))
                return

    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=20,
    )
    try:
        result = await news_api.get_latest(limit=count, page=1)
    except Exception as e:
        logger.error(f"News API error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    articles = (result.get("data") or []) if result else []
    if not articles:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_empty", lang))
        return

    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    await progress.update(80, get_text("progress_task_formatting", lang))

    lines = [get_text("news_title", lang) + "\n"]
    for article in articles[:count]:
        lines.append(format_news_article(article, lang))
        lines.append("")

    token = register_pagination_params(context.bot_data, params)
    logger.info(f"news_command: total={total}, total_pages={total_pages}, token={token!r}")
    keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None
    if keyboard:
        logger.info(f"news_command keyboard buttons: {[(b.text, b.callback_data) for row in keyboard.inline_keyboard for b in row]}")

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(
            chunk, reply_markup=keyboard, disable_web_page_preview=True
        )
        keyboard = None  # Only attach keyboard to first message
    await progress.complete(get_text("progress_task_result_ready", lang))


async def search_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/search_news <keyword> - Search news by keyword."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/search_news <keyword>"))
        return

    keyword = " ".join(context.args)
    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=20,
    )

    try:
        result = await news_api.search(keyword, limit=ITEMS_PER_PAGE, page=1)
    except Exception as e:
        logger.error(f"News search error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    articles = (result.get("data") or []) if result else []
    if not articles:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_no_results", lang))
        return

    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    title = get_text("news_search_title", lang, keyword=keyword)
    await progress.update(80, get_text("progress_task_formatting", lang))

    lines = [title + "\n"]
    for article in articles:
        lines.append(format_news_article(article, lang))
        lines.append("")

    token = register_pagination_params(context.bot_data, {"cmd": "search", "q": keyword, "title": title})
    keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, reply_markup=keyboard, disable_web_page_preview=True)
        keyboard = None
    await progress.complete(get_text("progress_task_result_ready", lang))


async def coin_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/coin_news <symbol> - News by coin."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/coin_news <BTC|ETH|SOL...>"))
        return

    coin = validate_coin_symbol(context.args[0])
    if not coin:
        await update.message.reply_text(get_text("error_usage", lang, usage="/coin_news <BTC|ETH|SOL...>"))
        return

    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=20,
    )
    try:
        result = await news_api.search_by_coin(coin, limit=ITEMS_PER_PAGE, page=1)
    except Exception as e:
        logger.error(f"Coin news error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    articles = (result.get("data") or []) if result else []
    if not articles:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_no_results", lang))
        return

    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    title = get_text("news_coin_title", lang, coin=coin)
    await progress.update(80, get_text("progress_task_formatting", lang))

    lines = [title + "\n"]
    for article in articles:
        lines.append(format_news_article(article, lang))
        lines.append("")

    token = register_pagination_params(context.bot_data, {"cmd": "coin", "coin": coin, "title": title})
    keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, reply_markup=keyboard, disable_web_page_preview=True)
        keyboard = None
    await progress.complete(get_text("progress_task_result_ready", lang))


async def hot_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/hot_news [min_score] - AI high-score news."""
    lang = await _get_lang(update, context)

    min_score = 70
    if context.args:
        try:
            min_score = int(context.args[0])
        except ValueError:
            pass

    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=20,
    )
    try:
        result = await news_api.get_high_score(min_score=min_score, limit=ITEMS_PER_PAGE, page=1)
    except Exception as e:
        logger.error(f"Hot news error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    articles = (result.get("data") or []) if result else []
    if not articles:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_no_results", lang))
        return

    title = get_text("news_hot_title", lang, score=min_score)
    await progress.update(80, get_text("progress_task_formatting", lang))
    lines = [title + "\n"]
    for article in articles:
        lines.append(format_news_article(article, lang))
        lines.append("")

    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    token = register_pagination_params(context.bot_data, {"cmd": "hot", "score": min_score, "title": title})
    keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, reply_markup=keyboard, disable_web_page_preview=True)
        keyboard = None
    await progress.complete(get_text("progress_task_result_ready", lang))


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/signal <long|short|neutral> - Filter by trading signal."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/signal <long|short|neutral>"))
        return

    signal = validate_signal(context.args[0])
    if not signal:
        await update.message.reply_text(get_text("error_usage", lang, usage="/signal <long|short|neutral>"))
        return

    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=20,
    )
    try:
        result = await news_api.get_by_signal(signal, limit=ITEMS_PER_PAGE, page=1)
    except Exception as e:
        logger.error(f"Signal news error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    articles = (result.get("data") or []) if result else []
    if not articles:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_no_results", lang))
        return

    title = get_text("news_signal_title", lang, signal=signal)
    await progress.update(80, get_text("progress_task_formatting", lang))
    lines = [title + "\n"]
    for article in articles:
        lines.append(format_news_article(article, lang))
        lines.append("")

    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    token = register_pagination_params(context.bot_data, {"cmd": "signal", "signal": signal, "title": title})
    keyboard = build_page_keyboard("news_page", 1, total_pages, token) if total_pages > 1 else None

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, reply_markup=keyboard, disable_web_page_preview=True)
        keyboard = None
    await progress.complete(get_text("progress_task_result_ready", lang))


async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sources - Browse all news sources."""
    lang = await _get_lang(update, context)
    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_sources", lang),
        percent=20,
    )

    try:
        result = await news_api.get_sources()
    except Exception as e:
        logger.error(f"Sources error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    data = result.get("data") or result
    if not data:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("news_no_results", lang))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    lines = [get_text("news_sources_title", lang) + "\n"]

    if isinstance(data, dict):
        for engine, sources in data.items():
            lines.append(f"📂 {engine}")
            if isinstance(sources, list):
                for s in sources[:10]:
                    name = s if isinstance(s, str) else s.get("name", str(s))
                    lines.append(f"   • {name}")
            elif isinstance(sources, dict):
                for key in list(sources.keys())[:10]:
                    lines.append(f"   • {key}")
            lines.append("")
    elif isinstance(data, list):
        for item in data[:30]:
            lines.append(f"   • {item}")

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))
