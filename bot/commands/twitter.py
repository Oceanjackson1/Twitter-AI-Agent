import logging
from telegram import Update
from telegram.ext import ContextTypes

from i18n.translator import get_text
from utils.formatters import format_tweet, format_user_profile, split_long_message
from utils.progress import ProgressMessage
from utils.validators import validate_username

logger = logging.getLogger(__name__)


async def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_repo = context.bot_data["user_repo"]
    return await user_repo.get_language(update.effective_user.id)


async def tw_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_user <username> - Get Twitter user profile."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_user <username>"))
        return

    username = validate_username(context.args[0])
    if not username:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_user <username>"))
        return

    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_profile", lang),
        percent=20,
    )
    try:
        result = await twitter_api.get_user(username)
    except Exception as e:
        logger.error(f"Twitter user error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    user_data = result.get("data") or result
    if not user_data:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_user_not_found", lang, username=username))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_user_title", lang, username=username)
    text = f"{title}\n{'─' * 28}\n{format_user_profile(user_data, lang)}"
    await update.message.reply_text(text, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def tw_tweets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_tweets <username> [count] - Get user's recent tweets."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_tweets <username> [count]"))
        return

    username = validate_username(context.args[0])
    if not username:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_tweets <username> [count]"))
        return

    count = 5
    if len(context.args) > 1:
        try:
            count = min(int(context.args[1]), 20)
        except ValueError:
            pass

    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_tweets", lang),
        percent=20,
    )
    try:
        result = await twitter_api.get_user_tweets_with_metrics(username, max_results=count)
    except Exception as e:
        logger.error(f"Twitter tweets error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    tweets = result.get("data") or result.get("tweets") or []
    if not tweets:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_no_results", lang))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_tweets_title", lang, username=username)
    lines = [title + "\n"]
    for tweet in tweets[:count]:
        lines.append(format_tweet(tweet))
        lines.append("─" * 28)

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def tw_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_search <keyword> - Search tweets by keyword."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_search <keyword>"))
        return

    keyword = " ".join(context.args)
    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_searching_twitter", lang),
        percent=20,
    )

    try:
        result = await twitter_api.search(keyword, max_results=10)
    except Exception as e:
        logger.error(f"Twitter search error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    tweets = result.get("data") or result.get("tweets") or []
    if not tweets:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_no_results", lang))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_search_title", lang, keyword=keyword)
    lines = [title + "\n"]
    for tweet in tweets[:10]:
        lines.append(format_tweet(tweet))
        lines.append("─" * 28)

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def tw_deleted_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_deleted <username> - Get deleted tweets."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_deleted <username>"))
        return

    username = validate_username(context.args[0])
    if not username:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_deleted <username>"))
        return

    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_deleted", lang),
        percent=20,
    )
    try:
        result = await twitter_api.get_deleted_tweets(username, max_results=10)
    except Exception as e:
        logger.error(f"Twitter deleted error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    tweets = result.get("data") or result.get("tweets") or []
    if not tweets:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_no_results", lang))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_deleted_title", lang, username=username)
    lines = [title + "\n"]
    for tweet in tweets[:10]:
        lines.append(format_tweet(tweet))
        lines.append("─" * 28)

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def tw_kol_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_kol <username> - Get KOL followers."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_kol <username>"))
        return

    username = validate_username(context.args[0])
    if not username:
        await update.message.reply_text(get_text("error_usage", lang, usage="/tw_kol <username>"))
        return

    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_kol", lang),
        percent=20,
    )
    try:
        result = await twitter_api.get_kol_followers(username)
    except Exception as e:
        logger.error(f"Twitter KOL error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    data = result.get("data") or []
    if not data:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_no_results", lang))
        return

    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_kol_title", lang, username=username)
    lines = [title + "\n"]
    for kol in data[:20]:
        name = kol.get("name", "")
        screen = kol.get("screenName", "")
        followers = kol.get("followersCount", kol.get("followers", 0))
        lines.append(f"👑 {name} (@{screen}) - {followers:,} followers")

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))


async def tw_followers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tw_followers <username> [follow|unfollow] - Follow/unfollow events."""
    lang = await _get_lang(update, context)

    if not context.args:
        await update.message.reply_text(
            get_text("error_usage", lang, usage="/tw_followers <username> [follow|unfollow]")
        )
        return

    username = validate_username(context.args[0])
    if not username:
        await update.message.reply_text(
            get_text("error_usage", lang, usage="/tw_followers <username> [follow|unfollow]")
        )
        return

    is_follow = True
    if len(context.args) > 1 and context.args[1].lower() == "unfollow":
        is_follow = False

    twitter_api = context.bot_data["twitter_api"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_fetching_followers", lang),
        percent=20,
    )
    try:
        result = await twitter_api.get_follower_events(username, is_follow=is_follow, max_results=10)
    except Exception as e:
        logger.error(f"Twitter followers error: {e}")
        await progress.fail(get_text("progress_task_failed", lang))
        await update.message.reply_text(get_text("error_api", lang))
        return

    data = result.get("data") or []
    if not data:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("tw_no_results", lang))
        return

    event_type = "Follow" if is_follow else "Unfollow"
    await progress.update(80, get_text("progress_task_formatting", lang))
    title = get_text("tw_followers_title", lang, username=username)
    lines = [f"{title} ({event_type})\n"]
    for event in data[:20]:
        name = event.get("name", event.get("screenName", ""))
        screen = event.get("screenName", "")
        ts = event.get("timestamp", event.get("createdAt", ""))
        lines.append(f"{'➕' if is_follow else '➖'} {name} (@{screen})  {ts}")

    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, disable_web_page_preview=True)
    await progress.complete(get_text("progress_task_result_ready", lang))
