#!/usr/bin/env python3
"""Surgical patch: Worker-401 fallback in bot/cards.py + robust _manual_post retest in bot/handlers.py + HANDOFF note."""

from __future__ import annotations

import py_compile
import tempfile
from pathlib import Path

CARDS = Path("bot/cards.py")
HANDLERS = Path("bot/handlers.py")
HANDOFF = Path("HANDOFF.md")

NEW_TCP = '''async def direct_tcp_test(host: str, port: int) - ‚ dict[str, Any]:
    """تست TCP مستقیم از خود ربات وقتی Worker جواب نمی‌دهد (همان منطق اسکریپت‌ها)."""

    def _run() - ‚ dict[str, Any]:
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ip = infos[0][4][0]
            if not ipaddress.ip_address(ip).is_global:
                return {"ok": False, "error": "non_global_ip"}
            started = time.time()
            with socket.create_connection((ip, port), timeout=8):
                pass
            return {"ok": True, "ip": ip, "latency_ms": int((time.time() - started) * 1000)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": type(exc).__name__}

    return await asyncio.to_thread(_run)


async def tcp_test(
    session: aiohttp.ClientSession,
    settings: Settings,
    parsed: ParsedConfig,
) - ‚ dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if settings.worker_secret:
        headers["X-Worker-Secret"] = settings.worker_secret
    worker_result: dict[str, Any] | None = None
    try:
        async with session.post(
            worker_test_url(settings.worker_url),
            json={"host": parsed.host, "port": parsed.port},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            data = await response.json(content_type=None)
            if response.status == 200 and isinstance(data, dict) and data.get("ok") and data.get("ip"):
                return data
            worker_result = data if isinstance(data, dict) else {"ok": False, "error": "worker_payload"}
    except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
        worker_result = {"ok": False, "error": "worker_unavailable"}
    fallback = await direct_tcp_test(parsed.host, parsed.port)
    if not fallback.get("ok") and isinstance(worker_result, dict) and worker_result.get("error"):
        fallback["worker_error"] = worker_result["error"]
    return fallback'''

HANDLERS_OLD = '''    _, fresh = await inspect_uri(record["uri"], ctx.settings, ctx.storage)
    await ctx.storage.save_config(config_id_value, fresh)
    if not fresh.get("healthy") or not fresh.get("ip"):
        await ctx.storage.append_admin_log(
            {"level": "error", "event": "manual_retest_failed", "config_id": config_id_value}
        )
        return False'''

HANDLERS_NEW = '''    fresh: dict[str, Any] = {}
    for attempt in range(2):
        try:
            _, fresh = await inspect_uri(record["uri"], ctx.settings, ctx.storage)
        except Exception:
            fresh = {}
        if fresh.get("healthy") and fresh.get("ip"):
            break
        if attempt == 0:
            await asyncio.sleep(2)
    if fresh.get("healthy") and fresh.get("ip"):
        await ctx.storage.save_config(config_id_value, fresh)
    elif (
        record.get("healthy")
        and record.get("ip")
        and time.time() - float(record.get("tested_at", 0)) < 3600
    ):
        await ctx.storage.append_admin_log(
            {"level": "warning", "event": "manual_retest_fallback_record", "config_id": config_id_value}
        )
    else:
        if fresh:
            await ctx.storage.save_config(config_id_value, fresh)
        await ctx.storage.append_admin_log(
            {"level": "error", "event": "manual_retest_failed", "config_id": config_id_value}
        )
        return False'''

HANDOFF_NOTE = '''

## ۱۵. پست‌مورم: «کانفیگ ارسال نمیشه» (2026-10-10 ~09:07 UTC)
- **ریشه:** تست مجددِ `_manual_post` در ربات فقط از Worker استفاده می‌کرد؛ Worker به‌خاطر ناهماهنگی `WORKER_SECRET` همیشه 401 می‌داد → `manual_retest_failed` (در `last_error` ثبت شد) → دکمهٔ «وصل شدم — ارسال فوری» و تأیید ارسال هرگز به کانال/گروه نمی‌رسید. اسکریپت‌ها (refresh/force/weekly) سبز بودند چون `direct_test` fallback سوکت مستقیم دارند؛ ربات این fallback را نداشت.
- **فیکس:** `bot/cards.py` → تابع `direct_tcp_test` (fallback سوکت مستقیم، همان منطق اسکریپت‌ها) داخل `tcp_test`؛ `bot/handlers.py` → در `_manual_post` دو تلاش تست با فاصله و در صورت شکست، استفاده از رکوردِ تازه و سالمِ ذخیره‌شده (کمتر از ۱ ساعت).
- **درس:** هر مسیر تستِ جدید باید fallback مستقیم داشته باشد؛ Worker دارای secret است و `WORKER_SECRET` ریپو با آن ناهماهنگ است (هماهنگ‌سازی همچنان باز است ولی اکنون الزامی نیست).'''


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"{label}: OK")


def main() -> None:
    replace_once(
        CARDS,
        "import base64\nimport json\n",
        "import asyncio\nimport base64\nimport ipaddress\nimport json\nimport socket\nimport time\n",
        "cards-imports",
    )

    text = CARDS.read_text(encoding="utf-8")
    start = text.index("async def tcp_test(")
    end_marker = 'return {"ok": False, "error": "worker_unavailable"}'
    end = text.index(end_marker, start) + len(end_marker)
    text = text[:start] + NEW_TCP + text[end:]
    CARDS.write_text(text, encoding="utf-8")
    print("cards-tcp_test: OK")

    replace_once(HANDLERS, HANDLERS_OLD, HANDLERS_NEW, "handlers-manual_post")

    for path in (CARDS, HANDLERS):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp_path = tmp.name
        py_compile.compile(str(path), cfile=tmp_path, doraise=True)
        print(f"compile {path}: OK")

    note = HANDOFF.read_text(encoding="utf-8")
    if "پست‌مورم: «کانفیگ ارسال نمیشه»" not in note:
        HANDOFF.write_text(note + HANDOFF_NOTE + "\n", encoding="utf-8")
        print("handoff-note: OK")

    print("PATCH_APPLIED")


if __name__ == "__main__":
    main()
