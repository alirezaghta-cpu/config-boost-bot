#!/usr/bin/env python3
"""Refresh public sources with only Python's standard library."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot.locales import fa  # noqa: E402

DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/config.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/all_configs.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Delta-Kronecker/V2ray-Config/main/All_Configs_Sub.txt",
]
URI_RE = re.compile(r"(?:vless|vmess|trojan|ss)://[^\s<>\'\"]+", re.IGNORECASE)
TEHRAN = ZoneInfo("Asia/Tehran")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"missing environment key: {name}")
    return value


CF_TOKEN = required("CLOUDFLARE_API_TOKEN")
CF_ACCOUNT = required("CLOUDFLARE_ACCOUNT_ID")
KV_NAMESPACE = required("KV_NAMESPACE_ID")
WORKER_URL = required("WORKER_URL").rstrip("/")
WORKER_SECRET = os.getenv("WORKER_SECRET", "").strip()
GITHUB_REPO = required("GITHUB_REPO")
GITHUB_TOKEN = required("GITHUB_TOKEN")
KV_BASE = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{CF_ACCOUNT}/storage/kv/namespaces/{KV_NAMESPACE}"
)


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 12,
) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def cf_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {CF_TOKEN}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def kv_get_text(key: str) -> str | None:
    status, body = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}"
        ,
        headers=cf_headers(),
    )
    if status == 404:
        return None
    if status >= 400:
        raise RuntimeError(f"KV read failed: HTTP {status}")
    return body.decode("utf-8")


def kv_get_json(key: str, default=None):
    raw = kv_get_text(key)
    if raw is None:
        return default
    return json.loads(raw)


def kv_put_text(key: str, value: str) -> None:
    status, body = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}"
        ,
        method="PUT",
        headers=cf_headers("text/plain; charset=utf-8"),
        data=value.encode("utf-8"),
    )
    if status >= 400:
        raise RuntimeError(f"KV write failed: HTTP {status}")


def kv_put_json(key: str, value) -> None:
    kv_put_text(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def kv_delete(key: str) -> None:
    status, _ = request(
        f"{KV_BASE}/values/{urllib.parse.quote(key, safe='')}"
        ,
        method="DELETE",
        headers=cf_headers(),
    )
    if status >= 400 and status != 404:
        raise RuntimeError(f"KV delete failed: HTTP {status}")


def kv_list(prefix: str) -> list[str]:
    names: list[str] = []
    cursor = ""
    while True:
        query = {"prefix": prefix, "limit": "1000"}
        if cursor:
            query["cursor"] = cursor
        status, body = request(
            f"{KV_BASE}/keys?{urllib.parse.urlencode(query)}",
            headers=cf_headers(),
        )
        if status >= 400:
            raise RuntimeError(f"KV list failed: HTTP {status}")
        payload = json.loads(body)
        if not payload.get("success"):
            raise RuntimeError("KV list failed")
        names.extend(item["name"] for item in payload.get("result", []))
        cursor = (payload.get("result_info") or {}).get("cursor") or ""
        if not cursor:
            return names


def fetch_text(url: str) -> str:
    status, body = request(url, headers={"User-Agent": "config-boost-bot/1.0"}, timeout=15)
    if status >= 400:
        raise RuntimeError(f"source HTTP {status}")
    return body.decode("utf-8", errors="ignore")


def extract_uris(text: str) -> list[str]:
    candidates = [text]
    compact = "".join(text.split())
    if compact and len(compact) % 4 in {0, 2, 3}:
        try:
            padded = compact + "=" * (-len(compact) % 4)
            candidates.append(base64.b64decode(padded).decode("utf-8", errors="ignore"))
        except (ValueError, UnicodeError):
            pass
    result: list[str] = []
    for candidate in candidates:
        for match in URI_RE.findall(candidate):
            uri = match.rstrip(".,;)")
            if uri:
                result.append(uri)
    return result


def b64decode_url(value: str) -> bytes:
    return base64.urlsafe_b64decode((value + "=" * (-len(value) % 4)).encode("ascii"))


def split_host_port(endpoint: str) -> tuple[str, int]:
    parsed = urllib.parse.urlsplit(f"//{endpoint}")
    if not parsed.hostname or parsed.port is None:
        raise ValueError("missing endpoint")
    return parsed.hostname, parsed.port


def parse_uri(uri: str) -> tuple[str, str, int]:
    protocol = uri.partition("://")[0].lower()
    if protocol in {"vless", "trojan"}:
        parsed = urllib.parse.urlsplit(uri)
        if not parsed.hostname or parsed.port is None:
            raise ValueError("missing endpoint")
        return protocol, parsed.hostname, parsed.port
    if protocol == "vmess":
        payload = uri[len("vmess://") :].split("#", 1)[0]
        data = json.loads(b64decode_url(payload).decode("utf-8"))
        return protocol, str(data["add"]), int(data["port"])
    if protocol == "ss":
        payload = urllib.parse.unquote(uri[len("ss://") :].split("#", 1)[0].split("?", 1)[0])
        if "@" not in payload:
            payload = b64decode_url(payload).decode("utf-8")
        _, endpoint = payload.rsplit("@", 1)
        host, port = split_host_port(endpoint)
        return protocol, host, port
    raise ValueError("unsupported protocol")


def direct_test(host: str, port: int) -> dict:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        ip = infos[0][4][0]
        if not ipaddress.ip_address(ip).is_global:
            return {"ok": False}
        started = time.time()
        with socket.create_connection((ip, port), timeout=8):
            pass
        return {"ok": True, "ip": ip, "latency_ms": int((time.time() - started) * 1000)}
    except Exception:
        return {"ok": False}


def worker_test(host: str, port: int) -> dict:
    endpoint = WORKER_URL if WORKER_URL.endswith("/test") else f"{WORKER_URL}/test"
    headers = {"Content-Type": "application/json", "User-Agent": "config-boost-bot/1.0"}
    if WORKER_SECRET:
        headers["X-Worker-Secret"] = WORKER_SECRET
    try:
        status, body = request(
            endpoint,
            method="POST",
            headers=headers,
            data=json.dumps({"host": host, "port": port}).encode("utf-8"),
            timeout=8,
        )
        if status == 200:
            payload = json.loads(body)
            if isinstance(payload, dict) and payload.get("ok"):
                return payload
    except Exception:
        pass
    return direct_test(host, port)


def flag(code: str) -> str:
    code = code.upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in code)


def geo_lookup(ip: str) -> dict:
    key = f"geo:{ip}"
    cached = kv_get_json(key, None)
    if isinstance(cached, dict) and time.time() - float(cached.get("ts", 0)) <= 86400:
        data = cached.get("data")
        return data if isinstance(data, dict) else {}
    if cached is not None:
        kv_delete(key)
    status, body = request(f"https://ipwho.is/{urllib.parse.quote(ip)}", timeout=8)
    if status != 200:
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict) or payload.get("success") is False:
        return {}
    code = str(payload.get("country_code") or "").upper()
    raw_country = str(payload.get("country") or "").strip() or None
    raw_city = str(payload.get("city") or "").strip() or None
    data = {
        "country": fa.COUNTRY_NAMES.get(code, raw_country),
        "city": fa.CITY_NAMES.get(raw_city or "", raw_city),
        "country_code": code or None,
        "flag": flag(code),
        "isp": str((payload.get("connection") or {}).get("isp") or "").strip() or None,
    }
    kv_put_json(key, {"ts": time.time(), "data": data})
    return data


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + 365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        + gd
        + gdm[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 14 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_now(ts: float) -> str:
    local = datetime.fromtimestamp(ts, TEHRAN)
    jy, jm, jd = gregorian_to_jalali(local.year, local.month, local.day)
    return f"{jy:04d}-{jm:02d}-{jd:02d} {local.hour:02d}:{local.minute:02d} {fa.TEHRAN_LABEL}"


def github_write_subscription(uris: list[str]) -> None:
    path = "data/subscription.txt"
    api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "config-boost-bot/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    status, body = request(f"{api}?ref=main", headers=headers)
    sha = None
    if status == 200:
        sha = json.loads(body).get("sha")
    elif status != 404:
        raise RuntimeError(f"GitHub read failed: HTTP {status}")
    content = ("\n".join(uris) + ("\n" if uris else "")).encode("utf-8")
    payload = {
        "message": "chore: refresh healthy subscription",
        "content": base64.b64encode(content).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    status, body = request(
        api,
        method="PUT",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    if status == 422 and b"identical" in body.lower():
        return
    if status not in {200, 201}:
        raise RuntimeError(f"GitHub write failed: HTTP {status}")


def rebuild_healthy() -> tuple[list[str], list[str]]:
    cutoff = time.time() - 7 * 86400
    ids: list[str] = []
    uris: list[str] = []
    for key in kv_list("config:"):
        record = kv_get_json(key, {})
        if (
            isinstance(record, dict)
            and record.get("healthy") is True
            and record.get("ip")
            and float(record.get("tested_at", 0)) >= cutoff
        ):
            item_id = key.split(":", 1)[1]
            ids.append(item_id)
            uris.append(str(record["uri"]))
    kv_put_json("configs:healthy", ids)
    return ids, uris


def main() -> None:
    sources = kv_get_json("sources", None)
    if not isinstance(sources, list):
        sources = DEFAULT_SOURCES

    found: list[str] = []
    seen: set[str] = set()
    source_errors: list[str] = []

    # Manual records that previously failed remain queued and are retried first.
    for key in kv_list("config:"):
        record = kv_get_json(key, {})
        if isinstance(record, dict) and not record.get("healthy") and record.get("uri"):
            uri = str(record["uri"])
            if uri not in seen:
                seen.add(uri)
                found.append(uri)

    for source in sources:
        if not str(source).startswith("https://"):
            continue
        try:
            for uri in extract_uris(fetch_text(str(source))):
                if uri not in seen:
                    seen.add(uri)
                    found.append(uri)
        except Exception as exc:
            source_errors.append(f"{source}: {type(exc).__name__}")

    tested = 0
    healthy_new = 0
    try:
        cursor = int(kv_get_text("refresh:cursor") or 0)
    except ValueError:
        cursor = 0
    if found:
        cursor %= len(found)
        window = (found[cursor:] + found[:cursor])[:30]
        kv_put_text("refresh:cursor", str((cursor + len(window)) % len(found)))
    else:
        window = []
    for uri in window:
        try:
            protocol, host, port = parse_uri(uri)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeError):
            continue
        tcp = worker_test(host, port)
        now = time.time()
        record = {
            "uri": uri,
            "protocol": protocol,
            "host": host,
            "port": port,
            "ip": tcp.get("ip"),
            "country": None,
            "city": None,
            "flag": "",
            "isp": None,
            "latency_ms": int(tcp.get("latency_ms") or 0),
            "tested_at": now,
            "tested_at_tehran": jalali_now(now),
            "healthy": bool(tcp.get("ok") and tcp.get("ip")),
            "queued": not bool(tcp.get("ok") and tcp.get("ip")),
        }
        if record["healthy"]:
            record.update(geo_lookup(str(record["ip"])))
            healthy_new += 1
        item_id = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:20]
        kv_put_json(f"config:{item_id}", record)
        tested += 1

    healthy_ids, healthy_uris = rebuild_healthy()
    github_write_subscription(healthy_uris)
    summary = {
        "ts": time.time(),
        "sources": len(sources),
        "found": len(found),
        "tested": tested,
        "healthy_new": healthy_new,
        "healthy_total": len(healthy_ids),
        "source_errors": source_errors,
    }
    kv_put_json("healthy:summary", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"refresh failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
