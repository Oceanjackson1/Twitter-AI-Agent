from __future__ import annotations

import json
import logging
import secrets
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from i18n.translator import get_text
from utils.formatters import format_news_article
from utils.progress import ProgressMessage

logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 5
PAGINATION_STORE_KEY = "pagination_states"
PAGINATION_TTL_SECONDS = 24 * 60 * 60
PAGINATION_MAX_ITEMS = 1024


def register_pagination_params(bot_data: dict, params: dict) -> str:
    """Store pagination params in bot state and return a short token."""
    states = bot_data.setdefault(PAGINATION_STORE_KEY, {})
    now = time.time()

    expired_tokens = [
        token for token, entry in states.items()
        if now - entry.get("created_at", 0) > PAGINATION_TTL_SECONDS
    ]
    for token in expired_tokens:
        states.pop(token, None)

    while len(states) >= PAGINATION_MAX_ITEMS:
        oldest_token = min(states, key=lambda token: states[token].get("created_at", 0))
        states.pop(oldest_token, None)

    token = secrets.token_urlsafe(6)
    states[token] = {
        "created_at": now,
        "params": params,
    }
    return token


def resolve_pagination_params(bot_data: dict, payload: str) -> dict | None:
    """Resolve pagination params from a short token or legacy JSON payload."""
    if not payload:
        return None

    if payload.startswith("{"):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    states = bot_data.get(PAGINATION_STORE_KEY, {})
    entry = states.get(payload)
    if not entry:
        return None
    return entry.get("params")


def build_page_keyboard(prefix: str, page: int, total_pages: int, token: str = "") -> InlineKeyboardMarkup:
    """Build pagination inline keyboard."""
    buttons = []
    if page > 1:
        prev_data = f"{prefix}:{page - 1}:{token}"
        logger.debug(f"Prev button callback_data: {prev_data!r} ({len(prev_data)} bytes)")
        buttons.append(InlineKeyboardButton("⬅️", callback_data=prev_data))
    buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        next_data = f"{prefix}:{page + 1}:{token}"
        logger.debug(f"Next button callback_data: {next_data!r} ({len(next_data)} bytes)")
        buttons.append(InlineKeyboardButton("➡️", callback_data=next_data))
    return InlineKeyboardMarkup([buttons]) if buttons else None


async def news_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle news pagination."""
    query = update.callback_query

    parts = query.data.split(":", 2)
    if len(parts) < 3:
        await query.answer()
        return
    _, page_str, params_str = parts
    page = int(page_str)

    user_repo = context.bot_data["user_repo"]
    lang = await user_repo.get_language(query.from_user.id)
    news_api = context.bot_data["news_api"]

    params = resolve_pagination_params(context.bot_data, params_str)
    if not params:
        await query.answer(get_text("page_expired", lang), show_alert=True)
        return

    await query.answer()
    progress = ProgressMessage(query.message, lang)
    await progress.update(25, get_text("progress_task_loading_page", lang))

    cmd = params.get("cmd", "news")
    try:
        result = await _fetch_news(news_api, cmd, params, page)
    except Exception as exc:
        logger.error(f"Pagination fetch error: {exc}")
        await progress.fail(get_text("progress_task_failed", lang))
        await query.answer(get_text("error_api", lang), show_alert=True)
        return

    if not result or not result.get("data"):
        await progress.complete(get_text("progress_task_no_results", lang))
        return

    articles = result["data"]
    total = result.get("total", len(articles))
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    await progress.update(75, get_text("progress_task_formatting", lang))

    title = params.get("title") or get_text("news_title", lang)
    text_parts = [f"{title}  ({get_text('page_info', lang, current=page, total=total_pages)})\n"]
    for article in articles:
        text_parts.append(format_news_article(article, lang))
        text_parts.append("")

    keyboard = build_page_keyboard("news_page", page, total_pages, params_str)
    await query.edit_message_text(
        "\n".join(text_parts),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def _fetch_news(news_api, cmd: str, params: dict, page: int):
    """Fetch news data based on command type and page."""
    limit = ITEMS_PER_PAGE
    if cmd == "news":
        return await news_api.get_latest(limit=limit, page=page)
    elif cmd == "search":
        return await news_api.search(params.get("q", ""), limit=limit, page=page)
    elif cmd == "coin":
        return await news_api.search_by_coin(params.get("coin", ""), limit=limit, page=page)
    elif cmd == "hot":
        return await news_api.get_high_score(min_score=params.get("score", 70), limit=limit, page=page)
    elif cmd == "signal":
        return await news_api.get_by_signal(params.get("signal", "long"), limit=limit, page=page)
    return None


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle noop button press (page counter)."""
    await update.callback_query.answer()
