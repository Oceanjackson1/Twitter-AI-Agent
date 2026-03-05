from __future__ import annotations

import logging
from typing import Iterable
from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from i18n.translator import get_text
from utils.progress import ProgressMessage, compose_progress_text
from utils.validators import validate_username

logger = logging.getLogger(__name__)

PENDING_MONITOR_KEY = "pending_monitor_requests"
PENDING_INPUT_KEY = "pending_input_requests"

DELIVERY_TELEGRAM = "telegram"
DELIVERY_GROUP = "group"
DELIVERY_WEBHOOK = "webhook"

OUTPUT_MESSAGE = "message"
OUTPUT_CSV = "csv"
OUTPUT_BOTH = "both"


def get_pending_monitor_store(bot_data: dict) -> dict:
    return bot_data.setdefault(PENDING_MONITOR_KEY, {})


def get_pending_input_store(bot_data: dict) -> dict:
    return bot_data.setdefault(PENDING_INPUT_KEY, {})


def pop_pending_monitor(bot_data: dict, user_id: int) -> dict | None:
    return get_pending_monitor_store(bot_data).pop(user_id, None)


def pop_pending_input(bot_data: dict, user_id: int) -> dict | None:
    return get_pending_input_store(bot_data).pop(user_id, None)


def parse_accounts(tokens: Iterable[str]) -> list[str]:
    raw = " ".join(tokens).replace("\n", " ").replace("，", ",")
    candidates = []
    for chunk in raw.split(","):
        for part in chunk.split():
            if part.strip():
                candidates.append(part.strip())

    accounts: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        username = validate_username(candidate)
        if not username:
            return []
        lowered = username.lower()
        if lowered not in seen:
            seen.add(lowered)
            accounts.append(lowered)
    return accounts


def build_monitor_delivery_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                get_text("monitor_delivery_dm", lang),
                callback_data="monitor_delivery:telegram",
            ),
            InlineKeyboardButton(
                get_text("monitor_delivery_group", lang),
                callback_data="monitor_delivery:group",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text("monitor_delivery_webhook", lang),
                callback_data="monitor_delivery:webhook",
            ),
        ],
    ])


def build_monitor_output_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                get_text("monitor_output_message", lang),
                callback_data="monitor_output:message",
            ),
            InlineKeyboardButton(
                get_text("monitor_output_csv", lang),
                callback_data="monitor_output:csv",
            ),
        ],
        [
            InlineKeyboardButton(
                get_text("monitor_output_both", lang),
                callback_data="monitor_output:both",
            ),
        ],
    ])


def build_monitor_keyword_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                get_text("monitor_keywords_skip", lang),
                callback_data="monitor_keywords:skip",
            ),
            InlineKeyboardButton(
                get_text("monitor_keywords_add", lang),
                callback_data="monitor_keywords:add",
            ),
        ]
    ])


def _is_valid_webhook_url(text: str) -> bool:
    parsed = urlparse(text.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def describe_delivery(lang: str, delivery_type: str, delivery_target: str | None, owner_user_id: int) -> str:
    if delivery_type == DELIVERY_WEBHOOK:
        return get_text("monitor_destination_webhook", lang, target=delivery_target or "-")
    if delivery_type == DELIVERY_GROUP:
        return get_text("monitor_destination_group", lang, target=delivery_target or "-")
    return get_text("monitor_destination_dm", lang, target=delivery_target or str(owner_user_id))


def describe_output_mode(lang: str, output_mode: str) -> str:
    key = {
        OUTPUT_MESSAGE: "monitor_output_message",
        OUTPUT_CSV: "monitor_output_csv",
        OUTPUT_BOTH: "monitor_output_both",
    }.get(output_mode, "monitor_output_message")
    return get_text(key, lang)


def summarize_accounts(accounts: list[str], limit: int = 3) -> str:
    if len(accounts) <= limit:
        return ", ".join(f"@{account}" for account in accounts)
    visible = ", ".join(f"@{account}" for account in accounts[:limit])
    return f"{visible} +{len(accounts) - limit}"


def build_monitor_stage_text(
    lang: str,
    task_key: str,
    percent: int,
    body: str,
    state: str = "running",
) -> str:
    return compose_progress_text(
        lang,
        get_text(task_key, lang),
        percent,
        body,
        state=state,
    )


async def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_repo = context.bot_data["user_repo"]
    return await user_repo.get_language(update.effective_user.id)


async def finalize_monitor_job(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    monitor_request: dict,
) -> dict:
    user_repo = context.bot_data["user_repo"]
    monitor_repo = context.bot_data["monitor_repo"]
    monitor_job_repo = context.bot_data["monitor_job_repo"]
    csv_exporter = context.bot_data["csv_exporter"]

    await user_repo.get_or_create(user_id)
    job = await monitor_job_repo.create_job(
        owner_user_id=user_id,
        delivery_type=monitor_request["delivery_type"],
        delivery_target=monitor_request.get("delivery_target"),
        output_mode=monitor_request["output_mode"],
        keywords=monitor_request.get("keywords"),
    )

    for account in monitor_request["accounts"]:
        monitor = await monitor_repo.add_monitor(account)
        await monitor_job_repo.add_account(job.id, monitor.id)

    if monitor_request["output_mode"] in {OUTPUT_CSV, OUTPUT_BOTH}:
        csv_path = csv_exporter.ensure_file(job.id)
        await monitor_job_repo.update_csv_file_path(job.id, csv_path)

    return await monitor_job_repo.get_job(job.id, owner_user_id=user_id)


async def ask_for_output_mode(
    reply_target,
    lang: str,
    accounts: list[str],
):
    await reply_target(
        build_monitor_stage_text(
            lang,
            "progress_task_choose_output",
            50,
            get_text("monitor_choose_output", lang, accounts=summarize_accounts(accounts)),
        ),
        reply_markup=build_monitor_output_keyboard(lang),
    )


async def ask_for_optional_keywords(
    reply_target,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    lang: str,
    monitor_request: dict,
    chat_id: int,
):
    get_pending_input_store(context.bot_data)[user_id] = {
        "kind": "monitor_keywords_text",
        "chat_id": chat_id,
    }
    await reply_target(
        build_monitor_stage_text(
            lang,
            "progress_task_choose_keywords",
            75,
            get_text(
                "monitor_keywords_prompt",
                lang,
                accounts=summarize_accounts(monitor_request["accounts"]),
                destination=describe_delivery(
                    lang,
                    monitor_request["delivery_type"],
                    monitor_request.get("delivery_target"),
                    user_id,
                ),
                output_mode=describe_output_mode(lang, monitor_request["output_mode"]),
            ),
        ),
        reply_markup=build_monitor_keyword_keyboard(lang),
    )


async def send_job_created_message(
    reply_target,
    lang: str,
    job: dict,
):
    destination = describe_delivery(
        lang,
        job["delivery_type"],
        job.get("delivery_target"),
        job["owner_user_id"],
    )
    output_mode = describe_output_mode(lang, job["output_mode"])
    text = get_text(
        "monitor_job_created",
        lang,
        job_id=job["id"],
        accounts=summarize_accounts(job["accounts"]),
        destination=destination,
        output_mode=output_mode,
        keywords=job.get("keywords") or get_text("monitor_keywords_none", lang),
    )
    if job["output_mode"] in {OUTPUT_CSV, OUTPUT_BOTH}:
        text += "\n" + get_text("monitor_csv_export_hint", lang, job_id=job["id"])
    await reply_target(
        build_monitor_stage_text(
            lang,
            "progress_task_result_ready",
            100,
            text,
            state="done",
        )
    )


async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/monitor <account1> [account2 ...] - Start a monitor job setup."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    accounts = parse_accounts(context.args)
    if not accounts:
        await update.message.reply_text(
            get_text("error_usage", lang, usage="/monitor <account1> [account2 account3 ...]")
        )
        return

    user_repo = context.bot_data["user_repo"]
    await user_repo.get_or_create(user_id, update.effective_user.username)

    get_pending_monitor_store(context.bot_data)[user_id] = {
        "accounts": accounts,
        "source_chat_id": update.effective_chat.id,
        "source_chat_type": update.effective_chat.type,
    }
    pop_pending_input(context.bot_data, user_id)

    await update.message.reply_text(
        build_monitor_stage_text(
            lang,
            "progress_task_choose_delivery",
            25,
            get_text("monitor_choose_delivery", lang, accounts=summarize_accounts(accounts)),
        ),
        reply_markup=build_monitor_delivery_keyboard(lang),
    )


async def monitor_bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/monitor_bind - Finish pending group delivery binding inside a group."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text(get_text("monitor_bind_group_only", lang))
        return

    pending_input = get_pending_input_store(context.bot_data).get(user_id)
    monitor_request = get_pending_monitor_store(context.bot_data).get(user_id)
    if not pending_input or pending_input.get("kind") != "monitor_group" or not monitor_request:
        await update.message.reply_text(get_text("monitor_bind_no_pending", lang))
        return

    monitor_request["delivery_type"] = DELIVERY_GROUP
    monitor_request["delivery_target"] = str(update.effective_chat.id)
    pop_pending_input(context.bot_data, user_id)

    await ask_for_output_mode(
        update.message.reply_text,
        lang,
        monitor_request["accounts"],
    )


async def pending_input_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pending monitor text inputs such as webhook URL or keyword text."""
    if not update.message:
        return

    user_id = update.effective_user.id
    pending_input = get_pending_input_store(context.bot_data).get(user_id)
    monitor_request = get_pending_monitor_store(context.bot_data).get(user_id)
    if not pending_input or not monitor_request:
        return

    if pending_input.get("chat_id") and pending_input["chat_id"] != update.effective_chat.id:
        return

    lang = await _get_lang(update, context)
    kind = pending_input.get("kind")

    if kind == "monitor_webhook":
        if update.effective_chat.type != "private":
            return
        webhook_url = (update.message.text or "").strip()
        if not _is_valid_webhook_url(webhook_url):
            await update.message.reply_text(get_text("monitor_invalid_webhook", lang))
            return
        monitor_request["delivery_type"] = DELIVERY_WEBHOOK
        monitor_request["delivery_target"] = webhook_url
        pop_pending_input(context.bot_data, user_id)
        await ask_for_output_mode(
            update.message.reply_text,
            lang,
            monitor_request["accounts"],
        )
        return

    if kind == "monitor_keywords_text":
        keywords = (update.message.text or "").strip()
        if not keywords:
            await update.message.reply_text(get_text("monitor_keywords_invalid", lang))
            return
        monitor_request["keywords"] = keywords
        pop_pending_input(context.bot_data, user_id)
        progress = await ProgressMessage.start(
            update.message.reply_text,
            lang,
            get_text("progress_task_creating_job", lang),
            percent=90,
        )
        job = await finalize_monitor_job(context, user_id, monitor_request)
        pop_pending_monitor(context.bot_data, user_id)
        await progress.complete(get_text("progress_task_result_ready", lang))
        await send_job_created_message(update.message.reply_text, lang, job)


async def unmonitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unmonitor <job_id|username> - Remove a monitor job."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            get_text("error_usage", lang, usage="/unmonitor <job_id|username>")
        )
        return

    monitor_job_repo = context.bot_data["monitor_job_repo"]
    monitor_repo = context.bot_data["monitor_repo"]
    job_ids: list[int] = []

    if context.args[0].isdigit():
        job_ids = [int(context.args[0])]
    else:
        username = validate_username(context.args[0])
        if not username:
            await update.message.reply_text(
                get_text("error_usage", lang, usage="/unmonitor <job_id|username>")
            )
            return
        matches = await monitor_job_repo.find_single_account_jobs(user_id, username)
        job_ids = [row["id"] for row in matches]
        if len(job_ids) > 1:
            await update.message.reply_text(get_text("monitor_unmonitor_ambiguous", lang))
            return

    if not job_ids:
        await update.message.reply_text(get_text("monitor_not_found", lang, username=context.args[0]))
        return

    removed_any = False
    for job_id in job_ids:
        orphan_monitor_ids = await monitor_job_repo.delete_job(user_id, job_id)
        if not orphan_monitor_ids:
            continue
        removed_any = True
        for monitor_id in orphan_monitor_ids:
            active_jobs = await monitor_job_repo.count_jobs_for_monitor(monitor_id)
            if active_jobs == 0:
                await monitor_repo.set_active(monitor_id, 0)

    if removed_any:
        await update.message.reply_text(get_text("monitor_job_removed", lang))
    else:
        await update.message.reply_text(get_text("monitor_not_found", lang, username=context.args[0]))


async def monitors_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/monitors - List monitor jobs."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    monitor_job_repo = context.bot_data["monitor_job_repo"]
    jobs = await monitor_job_repo.get_user_jobs(user_id)
    if not jobs:
        await update.message.reply_text(get_text("monitors_empty", lang))
        return

    lines = [get_text("monitors_title", lang) + "\n"]
    for job in jobs:
        destination = describe_delivery(
            lang,
            job["delivery_type"],
            job.get("delivery_target"),
            user_id,
        )
        output_mode = describe_output_mode(lang, job.get("output_mode") or OUTPUT_MESSAGE)
        accounts = job.get("accounts") or ""
        keywords = job.get("keywords") or get_text("monitor_keywords_none", lang)
        lines.append(
            get_text(
                "monitor_job_item",
                lang,
                job_id=job["id"],
                accounts=accounts,
                count=job["account_count"],
                destination=destination,
                output_mode=output_mode,
                keywords=keywords,
            )
        )

    await update.message.reply_text("\n".join(lines))


async def export_csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/export_csv <job_id> - Send the CSV file for a monitor job."""
    lang = await _get_lang(update, context)
    user_id = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            get_text("error_usage", lang, usage="/export_csv <job_id>")
        )
        return

    job_id = int(context.args[0])
    monitor_job_repo = context.bot_data["monitor_job_repo"]
    csv_exporter = context.bot_data["csv_exporter"]
    progress = await ProgressMessage.start(
        update.message.reply_text,
        lang,
        get_text("progress_task_exporting_csv", lang),
        percent=20,
    )
    job = await monitor_job_repo.get_job(job_id, owner_user_id=user_id)
    if not job:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("monitor_job_not_found", lang, job_id=job_id))
        return

    if job["output_mode"] not in {OUTPUT_CSV, OUTPUT_BOTH}:
        await progress.complete(get_text("progress_task_no_results", lang))
        await update.message.reply_text(get_text("monitor_csv_not_enabled", lang, job_id=job_id))
        return

    await progress.update(75, get_text("progress_task_formatting", lang))
    csv_path = job.get("csv_file_path") or csv_exporter.ensure_file(job_id)
    if not job.get("csv_file_path"):
        await monitor_job_repo.update_csv_file_path(job_id, csv_path)

    filename = f"monitor_job_{job_id}.csv"
    caption = get_text(
        "monitor_csv_export_caption",
        lang,
        job_id=job_id,
        accounts=summarize_accounts(job["accounts"]),
    )
    with open(csv_path, "rb") as csv_file:
        await update.message.reply_document(
            document=csv_file,
            filename=filename,
            caption=caption,
        )
    await progress.complete(get_text("progress_task_result_ready", lang))
