from telegram import Update
from telegram.ext import ContextTypes

from bot.commands.monitor import (
    DELIVERY_GROUP,
    DELIVERY_TELEGRAM,
    ask_for_optional_keywords,
    ask_for_output_mode,
    build_monitor_stage_text,
    describe_delivery,
    describe_output_mode,
    finalize_monitor_job,
    get_pending_input_store,
    get_pending_monitor_store,
    pop_pending_input,
    pop_pending_monitor,
    send_job_created_message,
)
from i18n.translator import get_text
from utils.progress import ProgressMessage


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language toggle inline button press."""
    query = update.callback_query
    await query.answer()

    user_repo = context.bot_data["user_repo"]
    user_id = query.from_user.id

    if query.data == "lang_zh":
        await user_repo.set_language(user_id, "zh", selected=True)
        await query.edit_message_text(get_text("lang_switched", "zh"))
        await query.message.reply_text(get_text("help_text", "zh"), disable_web_page_preview=True)
    elif query.data == "lang_en":
        await user_repo.set_language(user_id, "en", selected=True)
        await query.edit_message_text(get_text("lang_switched", "en"))
        await query.message.reply_text(get_text("help_text", "en"), disable_web_page_preview=True)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings inline button press."""
    query = update.callback_query
    await query.answer()

    user_repo = context.bot_data["user_repo"]
    user_id = query.from_user.id
    lang = await user_repo.get_language(user_id)
    data = query.data

    if data == "settings_alerts_50":
        await user_repo.update_settings(user_id, max_alerts=50)
    elif data == "settings_alerts_100":
        await user_repo.update_settings(user_id, max_alerts=100)
    elif data == "settings_alerts_200":
        await user_repo.update_settings(user_id, max_alerts=200)
    elif data == "settings_quiet_on":
        await user_repo.update_settings(user_id, quiet_start="23:00", quiet_end="07:00")
    elif data == "settings_quiet_off":
        await user_repo.update_settings(user_id, quiet_start=None, quiet_end=None)

    user = await user_repo.get_or_create(user_id)
    quiet = (
        get_text("settings_quiet", lang, start=user.quiet_start, end=user.quiet_end)
        if user.quiet_start
        else get_text("settings_quiet_none", lang)
    )
    text = (
        f"{get_text('settings_title', lang)}\n\n"
        f"{get_text('settings_max_alerts', lang, count=user.max_alerts)}\n"
        f"{quiet}\n\n"
        "✅ Updated"
    )
    await query.edit_message_text(text)


async def monitor_delivery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle monitor delivery choice callbacks."""
    query = update.callback_query
    await query.answer()

    user_repo = context.bot_data["user_repo"]
    user_id = query.from_user.id
    lang = await user_repo.get_language(user_id)

    monitor_request = get_pending_monitor_store(context.bot_data).get(user_id)
    if not monitor_request:
        await query.edit_message_text(get_text("monitor_pending_missing", lang))
        return

    delivery_choice = query.data.split(":", 1)[1]
    accounts = monitor_request["accounts"]

    if delivery_choice == DELIVERY_TELEGRAM:
        monitor_request["delivery_type"] = DELIVERY_TELEGRAM
        monitor_request["delivery_target"] = str(user_id)
        pop_pending_input(context.bot_data, user_id)
        await ask_for_output_mode(query.edit_message_text, lang, accounts)
        return

    if delivery_choice == "webhook":
        get_pending_input_store(context.bot_data)[user_id] = {
            "kind": "monitor_webhook",
            "chat_id": query.message.chat.id,
        }
        await query.edit_message_text(
            build_monitor_stage_text(
                lang,
                "progress_task_enter_webhook",
                50,
                get_text("monitor_webhook_prompt", lang, accounts=", ".join(f"@{a}" for a in accounts)),
            )
        )
        return

    if delivery_choice == DELIVERY_GROUP:
        if monitor_request.get("source_chat_type") in {"group", "supergroup"}:
            monitor_request["delivery_type"] = DELIVERY_GROUP
            monitor_request["delivery_target"] = str(query.message.chat.id)
            pop_pending_input(context.bot_data, user_id)
            await ask_for_output_mode(query.edit_message_text, lang, accounts)
            return

        get_pending_input_store(context.bot_data)[user_id] = {"kind": "monitor_group"}
        await query.edit_message_text(
            build_monitor_stage_text(
                lang,
                "progress_task_bind_group",
                50,
                get_text(
                    "monitor_group_prompt",
                    lang,
                    accounts=", ".join(f"@{a}" for a in accounts),
                ),
            )
        )


async def monitor_output_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle monitor output mode choice."""
    query = update.callback_query
    await query.answer()

    user_repo = context.bot_data["user_repo"]
    user_id = query.from_user.id
    lang = await user_repo.get_language(user_id)

    monitor_request = get_pending_monitor_store(context.bot_data).get(user_id)
    if not monitor_request:
        await query.edit_message_text(get_text("monitor_pending_missing", lang))
        return

    monitor_request["output_mode"] = query.data.split(":", 1)[1]
    await ask_for_optional_keywords(
        query.edit_message_text,
        context,
        user_id,
        lang,
        monitor_request,
        query.message.chat.id,
    )


async def monitor_keywords_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle optional keyword filter follow-up."""
    query = update.callback_query
    await query.answer()

    user_repo = context.bot_data["user_repo"]
    user_id = query.from_user.id
    lang = await user_repo.get_language(user_id)

    pending_input = get_pending_input_store(context.bot_data).get(user_id)
    monitor_request = get_pending_monitor_store(context.bot_data).get(user_id)
    if not pending_input or pending_input.get("kind") != "monitor_keywords_text" or not monitor_request:
        await query.edit_message_text(get_text("monitor_pending_missing", lang))
        return

    action = query.data.split(":", 1)[1]
    if action == "skip":
        pop_pending_input(context.bot_data, user_id)
        progress = ProgressMessage(query.message, lang)
        await progress.update(90, get_text("progress_task_creating_job", lang))
        job = await finalize_monitor_job(context, user_id, monitor_request)
        pop_pending_monitor(context.bot_data, user_id)
        await progress.complete(get_text("progress_task_result_ready", lang))
        await send_job_created_message(query.edit_message_text, lang, job)
        return

    await query.edit_message_text(
        build_monitor_stage_text(
            lang,
            "progress_task_enter_keywords",
            75,
            get_text(
                "monitor_keywords_entry",
                lang,
                accounts=", ".join(f"@{account}" for account in monitor_request["accounts"]),
                destination=describe_delivery(
                    lang,
                    monitor_request["delivery_type"],
                    monitor_request.get("delivery_target"),
                    user_id,
                ),
            ),
        ),
    )
