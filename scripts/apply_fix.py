#!/usr/bin/env python3
"""Apply fix: Worker-401 fallback in cards.tcp_test + robust _manual_post."""
import py_compile
import tempfile
from pathlib import Path

CARDS = Path("bot/cards.py")
HANDLERS = Path("bot/handlers.py")
HANDOFF = Path("HANDOFF.md")

NEW_TCP = '''async def direct_tcp_test(host, port):
    """Direct socket TCP test fallback (same as scripts/)."""
    def _run():
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ip = infos[0][4][0]
            if not ipaddress.ip_address(ip).is_global:
                return {"ok": False, "error": "non_global_ip"}
            started = time.time()
            with socket.create_connection((ip, port), timeout=8):
                pass
            return {"ok": True, "ip": ip, "latency_ms": int((time.time() - started) * 1000)}
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}
    return await asyncio.to_thread(_run)


async def tcp_test(session, settings, parsed):
    """Worker test with direct socket fallback (WORKER_SECRET mismatch returns 401)."""
    headers = {"Content-Type": "application/json"}
    if settings.worker_secret:
        headers["X-Worker-Secret"] = settings.worker_secret
    worker_result = None
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

HANDLERS_NEW = '''    fresh = {}
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

HANDOFF_NOTE = "\n\n## 15. Fix: manual send failing (2026-10-10)\n- Root cause: bot re-test called only the Worker; WORKER_SECRET mismatch -> 401 -> manual_retest_failed in last_error -> the admin 'send now' button never posted. Scripts were green because they have direct_test fallback; the bot had none.\n- Fix: direct_tcp_test fallback in bot/cards.py tcp_test + two retries and fresh-record (<1h) fallback in _manual_post (bot/handlers.py).\n- Lesson: every test path needs a direct fallback; aligning WORKER_SECRET with the deployed Worker is now optional, not required.\n"


def replace_once(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit("%s: expected 1 match in %s, found %d" % (label, path, count))
    path.write_text(text.replace(old, new), encoding="utf-8")
    print("%s: OK" % label)


def main():
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
    CARDS.write_text(text[:start] + NEW_TCP + text[end:], encoding="utf-8")
    print("cards-tcp_test: OK")
    replace_once(HANDLERS, HANDLERS_OLD, HANDLERS_NEW, "handlers-manual_post")
    for path in (CARDS, HANDLERS):
        tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        tmp.close()
        py_compile.compile(str(path), cfile=tmp.name, doraise=True)
        print("compile %s: OK" % path)
    note = HANDOFF.read_text(encoding="utf-8")
    if "manual send failing" not in note:
        HANDOFF.write_text(note + HANDOFF_NOTE, encoding="utf-8")
        print("handoff-note: OK")
    print("PATCh_APPLIED")


if __name__ == "__main__":
    main()
