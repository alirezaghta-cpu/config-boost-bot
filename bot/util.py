from __future__ import annotations

import hashlib
import html
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from bot.locales import fa

TEHRAN = ZoneInfo("Asia/Tehran")


def mask_secret(value: str | None) -> str:
    if not value:
        return "****"
    return f"{value[:8]}****"


def redact_text(text: object, secrets: Iterable[str]) -> str:
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, mask_secret(secret))
    return result


def tehran_now() -> datetime:
    return datetime.now(TEHRAN)


def jalali_datetime(value: datetime | float | int | None = None) -> str:
    if value is None:
        current = tehran_now()
    elif isinstance(value, (int, float)):
        current = datetime.fromtimestamp(value, TEHRAN)
    elif value.tzinfo is None:
        current = value.replace(tzinfo=TEHRAN)
    else:
        current = value.astimezone(TEHRAN)
    import jdatetime

    jalali = jdatetime.datetime.fromgregorian(datetime=current)
    return (
        f"{jalali.year:04d}-{jalali.month:02d}-{jalali.day:02d} "
        f"{jalali.hour:02d}:{jalali.minute:02d} {fa.TEHRAN_LABEL}"
    )


def config_id(uri: str) -> str:
    return hashlib.sha256(uri.strip().encode("utf-8")).hexdigest()[:20]


def escape_code(value: str) -> str:
    return html.escape(value, quote=False)


def country_flag(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in code)
