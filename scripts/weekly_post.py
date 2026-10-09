#!/usr/bin/env python3
"""پست هفتگی کانال و گروه با قفل cron، تست مجدد و گزارش خطای فقط-ادمین."""

from __future__ import annotations

import html
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot.locales import fa  # noqa: E402

LOCK_NAME = "weekly-post"
LOCK_TTL = 3000


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"missing environment key: {name}")
    return value


BOT_TOKEN = required("BOT_TOKEN")
CHANNEL_ID = int(required("CHANNEL_ID"))
GROUP_ID = int(required("GROUP_ID"))
BOT_USERNAME = required("BOT_USERNAME").lstrip("@")
WORKER_URL = required("WORKER_URL").rstrip("/")
WORKER_SECRET = os.getenv("WORKER_SECRET", "").strip()
ADMIN_IDS = [int(item) for item in required("ADMIN_IDS").split(",") if item.strip()]
CF_TOKEN = required("CLOUDFLARE_API_TOKEN")
CF_ACCOUNT = required("CLOUDFLARE_ACCOUNT_ID")
KV_NAMESPACE = required("KV_NAMESPACE_ID")
KV_BASE = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{CF_ACCOUNT}/storage/kv/namespaces/{KV_NAMESPACE}"
)


def request(url, *, method="GET", headers=None, data=None, timeout=15):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def kv_headers(content_type=None):
    headers = {"Authorization": f"Bearer {CF_TOKEN}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def kv_get_text(key):
    status, body = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}",
        headers=kv_headers(),
    )
    if status == 404:
        return None
    if status >= 400:
        raise RuntimeError(f"KV read failed: HTTP {status}")
    return body.decode("utf-8")


def kv_get_json(key, default=None):
    raw = kv_get_text(key)
    if raw is None:
        return default
    return json.loads(raw)


def kv_put_text(key, value):
    status, _ = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}",
        method="PUT",
        headers=kv_headers("text/plain; charset=utf-8"),
        data=value.encode("utf-8"),
    )
    if status >= 400:
        raise RuntimeError(f"KV write failed: HTTP {status}")


def kv_put_json(key, value):
    kv_put_text(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def kv_delete(key):
    status, _ = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}",
        method="DELETE",
        headers=kv_headers(),
    )
    if status not in {200, 204, 404}:
        raise RuntimeError(f"KV delete failed: HTTP {status}")


def acquire_lock() -> bool:
    raw = kv_get_text(f"lock:{LOCK_NAME}")
    if raw:
        try:
            lock = json.loads(raw)
            if time.time() - float(lock.get("ts", 0)) < LOCK_TTL:
                return False
        except (ValueError, TypeError):
            pass
    kv_put_json(f"lock:{LOCK_NAME}", {"ts": time.time(), "expires_at": time.time() + LOCK_TTL})
    return True


def telegram(method: str, payload: dict):
    status, body = request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, {}


def send_with_retry(payload: dict):
    status, data = telegram("sendMessage", payload)
    if status == 429:
        retry_after = int(((data.get("parameters") or {}).get("retry_after") or 5))
        time.sleep(retry_after + 1)
        status, data = telegram("sendMessage", payload)
        if status == 429:
            return False, "rate_limited"
    if status >= 400 or not data.get("ok"):
        return False, f"http_{status}"
    return True, "ok"


def notify_admin(text: str) -> None:
    for admin_id in ADMIN_IDS:
        status, data = telegram("sendMessage", {"chat_id": admin_id, "text": text})
        if status == 429:
            retry_after = int(((data.get("parameters") or {}).get("retry_after") or 5))
            time.sleep(retry_after + 1)
            telegram("sendMessage", {"chat_id": admin_id, "text": text})
        elif status >= 400:
            return


def worker_retest(host: str, port: int) -> dict:
    endpoint = WORKER_URL if WORKER_URL.endswith("/test") else f"{WORKER_URL}/test"
    headers = {"Content-Type": "application/json"}
    if WORKER_SECRET:
        headers["X-Worker-Secret"] = WORKER_SECRET
    status, body = request(
        endpoint,
        method="POST",
        headers=headers,
        data=json.dumps({"host": host, "port": port}).encode("utf-8"),
        timeout=10,
    )
    if status != 200:
        return {"ok": False}
    try:
        payload = json.loads(body)
        return payload if isinstance(payload, dict) else {"ok": False}
    except json.JSONDecodeError:
        return {"ok": False}


def channel_buttons(config_id: str) -> dict:
    link = f"https://t.me/{BOT_USERNAME}?start=cfg_{config_id}"
    return {
        "inline_keyboard": [
            [{"text": fa.BTN_TEST, "url": link}],
            [{"text": fa.BTN_COPY_FROM_BOT, "url": link}],
        ]
    }


def is_post_due(mode: str, last_ts: float) -> bool:
    now = time.time()
    if mode == "d3":
        return now - last_ts >= 3 * 86400
    return now - last_ts >= 6 * 86400


def main() -> None:
    if not acquire_lock():
        print("locked; skipping")
        return
    try:
        mode = (kv_get_text("post:mode") or "weekly").strip()
        if mode not in {"weekly", "d3", "off"}:
            mode = "weekly"
        auto = (kv_get_text("auto_post") or "on").strip() != "off"
        if mode == "off" or not auto:
            print("posting disabled")
            return

        last_post = kv_get_json("last_post", {}) or {}
        last_ts = float(last_post.get("ts", 0) or 0)
        if not is_post_due(mode, last_ts):
            print("not due")
            return

        candidates = []
        ids = kv_get_json("configs:healthy", []) or []
        cutoff = time.time() - 7 * 86400
        for item_id in ids:
            record = kv_get_json(f"config:{item_id}", None)
            if not isinstance(record, dict) or not record.get("healthy") or not record.get("ip"):
                continue
            if float(record.get("tested_at", 0)) < cutoff:
                continue
            posted_raw = kv_get_text(f"posted:{item_id}")
            try:
                posted_ts = float(posted_raw or 0)
            except ValueError:
                posted_ts = 0
            if time.time() - posted_ts < 7 * 86400:
                continue
            record["id"] = str(item_id)
            candidates.append(record)

        if not candidates:
            notify_admin(fa.CRON_NO_CONFIG_ADMIN)
            return

        selected = random.choice(candidates)
        tcp = worker_retest(str(selected["host"]), int(selected["port"]))
        if not (tcp.get("ok") and tcp.get("ip")):
            notify_admin(fa.POST_TEST_FAILED_ADMIN)
            kv_put_json(
                "last_error",
                {"ts": time.time(), "event": "weekly_retest_failed", "config_id": selected["id"]},
            )
            return

        text = fa.channel_post(selected, BOT_USERNAME, html.escape(str(selected["uri"]), quote=False))
        reply_markup = channel_buttons(selected["id"])
        sent = []
        for chat_id in (CHANNEL_ID, GROUP_ID):
            ok, reason = send_with_retry(
                {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup,
                }
            )
            if ok:
                sent.append(chat_id)
            else:
                notify_admin(fa.post_admin_error(f"{chat_id}: {reason}"))
                if reason == "rate_limited":
                    notify_admin(fa.POST_RATE_LIMIT_ADMIN)
                    break

        if sent:
            now = time.time()
            kv_put_text(f"posted:{selected['id']}", str(now))
            kv_put_json("last_post", {"ts": now, "config_id": selected["id"], "targets": sent})
            if len(sent) < 2:
                notify_admin(fa.POST_PARTIAL_ADMIN)
            print(json.dumps({"posted": selected["id"], "targets": sent}))
        else:
            kv_put_json(
                "last_error",
                {"ts": time.time(), "event": "weekly_post_failed", "config_id": selected["id"]},
            )
    finally:
        kv_delete(f"lock:{LOCK_NAME}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"weekly_post failed: {type(exc).__name__}", file=sys.stderr)
        try:
            notify_admin(fa.post_admin_error(type(exc).__name__))
        except Exception:
            pass
        raise SystemExit(1)
