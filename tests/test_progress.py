"""T1.3: Unit tests for utils/progress.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock

import pytest

from utils.progress import ProgressMessage, build_progress_bar, render_progress_text


def test_p1_build_progress_bar():
    assert build_progress_bar(0) == "[----------]"
    assert build_progress_bar(50) == "[#####-----]"
    assert build_progress_bar(100) == "[##########]"


def test_p2_render_progress_text():
    text = render_progress_text("en", "running", "Fetching news data", 40)
    assert "Processing request" in text
    assert "Current task: Fetching news data" in text
    assert "[####------] 40%" in text


@pytest.mark.asyncio
async def test_p3_progress_message_updates_state():
    status_message = AsyncMock()
    reply_target = AsyncMock(return_value=status_message)

    progress = await ProgressMessage.start(reply_target, "en", "Preparing your request", percent=10)
    await progress.update(60, "Formatting results")
    await progress.complete("Result is ready")

    first_text = reply_target.call_args.args[0]
    assert "Preparing your request" in first_text
    status_message.edit_text.assert_any_await("✅ Completed\nCurrent task: Result is ready\nProgress: [##########] 100%")
