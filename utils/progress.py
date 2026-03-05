from __future__ import annotations

import logging
from dataclasses import dataclass

from i18n.translator import get_text

logger = logging.getLogger(__name__)


def build_progress_bar(percent: int, width: int = 10) -> str:
    percent = max(0, min(100, int(percent)))
    width = max(1, width)
    filled = round((percent / 100) * width)
    return f"[{'#' * filled}{'-' * (width - filled)}]"


def render_progress_text(lang: str, state: str, task: str, percent: int) -> str:
    title_key = {
        "running": "progress_running",
        "done": "progress_done",
        "failed": "progress_failed",
    }.get(state, "progress_running")
    clamped = max(0, min(100, int(percent)))
    return "\n".join([
        get_text(title_key, lang),
        get_text("progress_task_line", lang, task=task),
        get_text(
            "progress_bar_line",
            lang,
            bar=build_progress_bar(clamped),
            percent=clamped,
        ),
    ])


def compose_progress_text(
    lang: str,
    task: str,
    percent: int,
    body: str,
    state: str = "running",
) -> str:
    header = render_progress_text(lang, state, task, percent)
    return f"{header}\n\n{body}".strip()


@dataclass
class ProgressMessage:
    message: object | None
    lang: str
    state: str = "running"
    percent: int = 0
    task: str = ""
    _last_text: str = ""

    @classmethod
    async def start(
        cls,
        reply_target,
        lang: str,
        task: str,
        percent: int = 10,
    ) -> "ProgressMessage":
        text = render_progress_text(lang, "running", task, percent)
        message = None
        try:
            message = await reply_target(text)
        except Exception as exc:
            logger.warning("Failed to send progress message: %s", exc)
        return cls(
            message=message,
            lang=lang,
            state="running",
            percent=percent,
            task=task,
            _last_text=text,
        )

    async def update(self, percent: int, task: str) -> None:
        self.state = "running"
        self.percent = percent
        self.task = task
        await self._apply()

    async def complete(self, task: str | None = None) -> None:
        self.state = "done"
        self.percent = 100
        self.task = task or get_text("progress_task_result_ready", self.lang)
        await self._apply()

    async def fail(self, task: str | None = None) -> None:
        self.state = "failed"
        self.percent = max(5, min(99, int(self.percent or 5)))
        self.task = task or get_text("progress_task_failed", self.lang)
        await self._apply()

    async def _apply(self) -> None:
        if not self.message:
            return
        text = render_progress_text(self.lang, self.state, self.task, self.percent)
        if text == self._last_text:
            return
        try:
            await self.message.edit_text(text)
            self._last_text = text
        except Exception as exc:
            logger.debug("Skipping progress update because message edit failed: %s", exc)
