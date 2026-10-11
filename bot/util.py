from __future__ import annotations

import base64
import hashlib
import html
import json
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


def config_identity(uri: str) -> str:
    """Same server group -> same identity, ignoring the IP.

    The same provider republishes identical uuid/pbk/sni entries on a different
    IP; readers see that as a duplicate config. Identity-based exclusion stops
    the test panel and the auto-post from resending it.
    """
    try:
        if uri.startswith("vless://"):
            body = uri[8:]
            uuid_part, _, rest = body.partition("@")
            hostport, _, query = rest.partition("?")
            _, _, port = hostport.rpartition(":")
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return "|".join(
                [
                    "vless",
                    uuid_part,
                    params.get("pbk", ""),
                    params.get("sni", ""),
                    params.get("sid", ""),
                    port.split("#")[0],
                ]
            )
        if uri.startswith("trojan://"):
            body = uri[9:]
            _, _, rest = body.partition("@")
            hostport, _, query = rest.partition("?")
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return "|".join(["trojan", hostport.split("#")[0], params.get("sni", "")])
        if uri.startswith("vmess://"):
            raw = uri[8:]
            raw += "=" * (-len(raw) % 4)
            data = json.loads(base64.urlsafe_b64decode(raw).decode("utf-8", "ignore"))
            return "|".join(
                [
                    "vmess",
                    str(data.get("add") or ""),
                    str(data.get("id") or ""),
                    str(data.get("port") or ""),
                    str(data.get("sni") or data.get("host") or ""),
                ]
            )
        if uri.startswith("ss://"):
            head, _, tail = uri[5:].partition("@")
            hostport = tail.split("?")[0].split("#")[0]
            return "|".join(["ss", hostport, head[:32]])
    except Exception:
        pass
    return uri[:96]


def escape_code(value: str) -> str:
    return html.escape(value, quote=False)


def country_flag(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in code)
