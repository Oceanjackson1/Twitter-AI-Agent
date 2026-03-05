import asyncio
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from i18n.translator import get_text
from utils.constants import (
    ASK_SYSTEM_PROMPT,
    ANALYZE_SYSTEM_PROMPT,
    BRIEFING_SYSTEM_PROMPT,
    LANG_MAP,
)
from utils.formatters import format_news_article, format_tweet, split_long_message
from utils.progress import ProgressMessage

logger = logging.getLogger(__name__)
AI_HISTORY_LIMIT = 8


async def _get_ai_history(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list[dict]:
    ai_repo = context.bot_data.get("ai_repo")
    if not ai_repo:
        return []
    return await ai_repo.get_recent_messages(user_id, limit=AI_HISTORY_LIMIT)


async def _remember_exchange(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    user_message: str,
    assistant_message: str,
    mode: str,
) -> None:
    ai_repo = context.bot_data.get("ai_repo")
    if not ai_repo:
        return
    await ai_repo.add_exchange(user_id, user_message, assistant_message, mode=mode)


async def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_repo = context.bot_data["user_repo"]
    return await user_repo.get_language(update.effective_user.id)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask <question> - Ask AI about crypto markets."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/ask <question>"))
        return

    question = " ".join(context.args)
    deepseek = context.bot_data["deepseek"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_loading_memory", lang),
        percent=15,
    )

    await update.effective_chat.send_action(ChatAction.TYPING)

    try:
        system = ASK_SYSTEM_PROMPT.format(language=LANG_MAP.get(lang, "English"))
        history = await _get_ai_history(context, user_id)
        await progress.update(50, get_text("progress_task_generating_ai", lang))
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": question}]
        answer = await deepseek.chat_messages(messages)
        await _remember_exchange(context, user_id, question, answer, mode="ask")
    except Exception as e:
        logger.error(f"Deepseek ask error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("ai_error", lang))
        return

    await progress.update(90, get_text("progress_task_formatting", lang))
    for chunk in split_long_message(f"🤖 AI:\n\n{answer}"):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/analyze <coin|topic> - Deep AI analysis."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/analyze <coin|topic>"))
        return

    topic = " ".join(context.args)
    deepseek = context.bot_data["deepseek"]
    news_api = context.bot_data["news_api"]
    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_collecting_context", lang),
        percent=15,
    )

    await update.effective_chat.send_action(ChatAction.TYPING)

    # Fetch news and tweets in parallel
    try:
        news_task = asyncio.create_task(news_api.search(topic, limit=10, page=1))
        tweets_task = asyncio.create_task(twitter_api.search(topic, max_results=10))
        news_result, tweets_result = await asyncio.gather(news_task, tweets_task, return_exceptions=True)
    except Exception as e:
        logger.error(f"Data fetch error for analyze: {e}")
        news_result = {}
        tweets_result = {}

    # Build context string
    context_parts = [f"Topic: {topic}\n"]

    # News data
    if isinstance(news_result, dict):
        articles = news_result.get("data") or []
        if articles:
            context_parts.append("=== NEWS DATA ===")
            for a in articles[:10]:
                context_parts.append(format_news_article(a, "en"))
                context_parts.append("")

    # Twitter data
    if isinstance(tweets_result, dict):
        tweets = tweets_result.get("data") or tweets_result.get("tweets") or []
        if tweets:
            context_parts.append("=== TWITTER DATA ===")
            for t in tweets[:10]:
                context_parts.append(format_tweet(t))
                context_parts.append("")

    context_str = "\n".join(context_parts)

    try:
        await progress.update(45, get_text("progress_task_loading_memory", lang))
        system = ANALYZE_SYSTEM_PROMPT.format(
            topic=topic, language=LANG_MAP.get(lang, "English")
        )
        history = await _get_ai_history(context, user_id)
        await progress.update(75, get_text("progress_task_generating_ai", lang))
        messages = [
            {"role": "system", "content": system},
            *history,
            {
                "role": "user",
                "content": f"Please analyze {topic} with the following fresh market context:\n\n{context_str}",
            },
        ]
        answer = await deepseek.chat_messages(messages, max_tokens=3000)
        await _remember_exchange(context, user_id, f"Analyze {topic}", answer, mode="analyze")
    except Exception as e:
        logger.error(f"Deepseek analyze error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("ai_error", lang))
        return

    await progress.update(90, get_text("progress_task_formatting", lang))
    for chunk in split_long_message(f"🤖 {topic} Analysis:\n\n{answer}"):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/briefing - AI daily market briefing."""
    lang = await _get_lang(update, context)
    deepseek = context.bot_data["deepseek"]
    news_api = context.bot_data["news_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_news", lang),
        percent=15,
    )

    await update.effective_chat.send_action(ChatAction.TYPING)

    # Fetch high-score news
    try:
        result = await news_api.get_high_score(min_score=60, limit=20, page=1)
    except Exception as e:
        logger.error(f"Briefing news fetch error: {e}")
        result = {}

    articles = (result.get("data") or []) if isinstance(result, dict) else []

    context_parts = ["=== TODAY'S HIGH-SCORE NEWS ===\n"]
    for a in articles[:20]:
        context_parts.append(format_news_article(a, "en"))
        context_parts.append("")

    context_str = "\n".join(context_parts)

    try:
        await progress.update(60, get_text("progress_task_generating_briefing", lang))
        system = BRIEFING_SYSTEM_PROMPT.format(language=LANG_MAP.get(lang, "English"))
        answer = await deepseek.chat(context_str, system_prompt=system, max_tokens=2500)
    except Exception as e:
        logger.error(f"Deepseek briefing error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("ai_error", lang))
        return

    await progress.update(90, get_text("progress_task_formatting", lang))
    for chunk in split_long_message(f"📊 Daily Briefing:\n\n{answer}"):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))
