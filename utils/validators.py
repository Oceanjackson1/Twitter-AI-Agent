from __future__ import annotations

import re


def validate_username(text: str) -> str | None:
    """Validate a username, @handle, or x.com/twitter.com profile URL."""
    candidate = text.strip()
    url_match = re.match(
        r"^(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/([A-Za-z0-9_]{1,15})(?:[/?#].*)?$",
        candidate,
        re.IGNORECASE,
    )
    if url_match:
        return url_match.group(1)

    name = candidate.lstrip("@")
    if re.match(r"^[A-Za-z0-9_]{1,15}$", name):
        return name
    return None


def validate_coin_symbol(text: str) -> str | None:
    """Uppercase and validate coin symbol. Returns cleaned symbol or None."""
    symbol = text.strip().upper()
    if re.match(r"^[A-Z0-9]{1,10}$", symbol):
        return symbol
    return None


def validate_signal(text: str) -> str | None:
    """Validate trading signal value."""
    val = text.strip().lower()
    if val in ("long", "short", "neutral"):
        return val
    return None
