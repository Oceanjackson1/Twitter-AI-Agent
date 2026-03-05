import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from i18n.translator import get_text

logger = logging.getLogger(__name__)


async def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_repo = context.bot_data["user_repo"]
    return await user_repo.get_language(update.effective_user.id)


async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/me - View account info."""
    lang = await _get_lang(update, context)
    user_repo = context.bot_data["user_repo"]
    monitor_job_repo = context.bot_data["monitor_job_repo"]

    user = await user_repo.get_or_create(
        update.effective_user.id, update.effective_user.username
    )
    jobs = await monitor_job_repo.get_user_jobs(user.user_id)
    lang_display = "中文" if user.language == "zh" else "English"

    lines = [
        get_text("me_title", lang),
        "─" * 28,
        get_text("me_language", lang, language=lang_display),
        get_text("me_monitors", lang, count=len(jobs)),
        get_text("me_created", lang, date=user.created_at or "N/A"),
    ]
    await update.message.reply_text("\n".join(lines))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/settings - Configure alert preferences."""
    lang = await _get_lang(update, context)
    user_repo = context.bot_data["user_repo"]
    user = await user_repo.get_or_create(
        update.effective_user.id, update.effective_user.username
    )

    quiet = (
        get_text("settings_quiet", lang, start=user.quiet_start, end=user.quiet_end)
        if user.quiet_start
        else get_text("settings_quiet_none", lang)
    )

    text = (
        f"{get_text('settings_title', lang)}\n"
        f"{'─' * 28}\n"
        f"{get_text('settings_max_alerts', lang, count=user.max_alerts)}\n"
        f"{quiet}\n\n"
        f"{'选择每日最大告警数:' if lang == 'zh' else 'Max daily alerts:'}"
    )

    keyboard = [
        [
            InlineKeyboardButton("50", callback_data="settings_alerts_50"),
            InlineKeyboardButton("100", callback_data="settings_alerts_100"),
            InlineKeyboardButton("200", callback_data="settings_alerts_200"),
        ],
        [
            InlineKeyboardButton(
                "🌙 23:00-07:00" if lang == "zh" else "🌙 Quiet 23:00-07:00",
                callback_data="settings_quiet_on",
            ),
            InlineKeyboardButton(
                "🔔 关闭静默" if lang == "zh" else "🔔 No Quiet",
                callback_data="settings_quiet_off",
            ),
        ],
    ]

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )
