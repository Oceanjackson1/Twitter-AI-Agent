from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from i18n.translator import get_text


def build_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("中文", callback_data="lang_zh"),
            InlineKeyboardButton("English", callback_data="lang_en"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_repo = context.bot_data["user_repo"]
    user_record = await user_repo.get_or_create(user.id, user.username)
    if not user_record.language_selected:
        await update.message.reply_text(
            get_text("choose_language", "zh"),
            reply_markup=build_language_keyboard(),
        )
        return

    lang = user_record.language
    await update.message.reply_text(get_text("help_text", lang), disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_repo = context.bot_data["user_repo"]
    lang = await user_repo.get_language(update.effective_user.id)
    await update.message.reply_text(get_text("help_text", lang), disable_web_page_preview=True)


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        get_text("choose_language", "zh"),
        reply_markup=build_language_keyboard(),
    )
