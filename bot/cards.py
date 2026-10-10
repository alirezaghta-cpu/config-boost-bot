from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import aiohttp
import qrcode

from bot.config import Settings
from bot.locales import fa
from bot.storage import KVStorage
from bot.util import config_id, country_flag, jalali_datetime


class ConfigParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedConfig:
    protocol: str
    host: str
    port: int
    security: str | None = None


def _b64decode(value: str) -> bytes:
    clean = value.strip()
    clean += "=" * (-len(clean) % 4)
    try:
        return base64.urlsafe_b64decode(clean.encode("ascii"))
    except (ValueError, UnicodeError) as exc:
        raise ConfigParseError("invalid base64") from exc


def _host_port(value: str) -> tuple[str, int]:
    parsed = urlsplit(f"//{value}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConfigParseError("invalid port") from exc
    if not parsed.hostname or port is None:
        raise ConfigParseError("missing host or port")
    if not 1 <= port <= 65535:
        raise ConfigParseError("invalid port")
    return parsed.hostname, port


def parse_config_uri(uri: str) -> ParsedConfig:
    raw = uri.strip()
    scheme = raw.partition("://")[0].lower()
    if scheme not in {"vless", "vmess", "trojan", "ss"}:
        raise ConfigParseError("unsupported protocol")

    if scheme in {"vless", "trojan"}:
        parsed = urlsplit(raw)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ConfigParseError("invalid port") from exc
        if not parsed.hostname or port is None:
            raise ConfigParseError("missing host or port")
        query = parse_qs(parsed.query, keep_blank_values=True)
        security = str((query.get("security") or [""])[0]).strip() or None
        return ParsedConfig(scheme, parsed.hostname, port, security)

    if scheme == "vmess":
        payload = raw[len("vmess://") :].split("#", 1)[0].strip()
        try:
            data = json.loads(_b64decode(payload).decode("utf-8"))
            host = str(data.get("add") or data.get("host") or "").strip()
            port = int(data.get("port"))
            security = str(data.get("tls") or data.get("security") or "").strip() or None
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            raise ConfigParseError("invalid vmess") from exc
        if not host or not 1 <= port <= 65535:
            raise ConfigParseError("invalid vmess endpoint")
        return ParsedConfig(scheme, host, port, security)

    payload = raw[len("ss://") :].split("#", 1)[0].split("?", 1)[0]
    payload = unquote(payload)
    if "@" in payload:
        _, endpoint = payload.rsplit("@", 1)
    else:
        try:
            decoded = _b64decode(payload).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConfigParseError("invalid ss") from exc
        if "@" not in decoded:
            raise ConfigParseError("invalid ss endpoint")
        _, endpoint = decoded.rsplit("@", 1)
    host, port = _host_port(endpoint)
    return ParsedConfig(scheme, host, port)


def worker_test_url(worker_url: str) -> str:
    clean = worker_url.rstrip("/")
    return clean if clean.endswith("/test") else f"{clean}/test"


async def tcp_test(
    session: aiohttp.ClientSession,
    settings: Settings,
    parsed: ParsedConfig,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if settings.worker_secret:
        headers["X-Worker-Secret"] = settings.worker_secret
    try:
        async with session.post(
            worker_test_url(settings.worker_url),
            json={"host": parsed.host, "port": parsed.port},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            data = await response.json(content_type=None)
            if response.status != 200:
                return {"ok": False, "error": f"worker_http_{response.status}"}
            return data if isinstance(data, dict) else {"ok": False, "error": "worker_payload"}
    except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
        return {"ok": False, "error": "worker_unavailable"}


async def geo_lookup(
    session: aiohttp.ClientSession,
    storage: KVStorage,
    ip: str,
) -> dict[str, Any]:
    cached = await storage.get_geo(ip)
    if cached is not None:
        return cached
    try:
        async with session.get(
            f"https://ipwho.is/{ip}",
            timeout=aiohttp.ClientTimeout(total=8),
        ) as response:
            data = await response.json(content_type=None)
            if response.status != 200 or not isinstance(data, dict) or data.get("success") is False:
                return {}
    except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
        return {}

    code = str(data.get("country_code") or "").upper()
    raw_country = str(data.get("country") or "").strip() or None
    raw_city = str(data.get("city") or "").strip() or None
    geo = {
        "country": fa.COUNTRY_NAMES.get(code, raw_country),
        "city": fa.CITY_NAMES.get(raw_city or "", raw_city),
        "country_code": code or None,
        "flag": country_flag(code),
        "isp": str((data.get("connection") or {}).get("isp") or "").strip() or None,
    }
    await storage.set_geo(ip, geo)
    return geo


async def inspect_uri(
    uri: str,
    settings: Settings,
    storage: KVStorage,
    session: aiohttp.ClientSession | None = None,
) -> tuple[str, dict[str, Any]]:
    parsed = parse_config_uri(uri)
    owns_session = session is None
    client = session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
    try:
        tcp = await tcp_test(client, settings, parsed)
        now_ts = __import__("time").time()
        record: dict[str, Any] = {
            "uri": uri.strip(),
            "protocol": parsed.protocol,
            "host": parsed.host,
            "port": parsed.port,
            "security": parsed.security,
            "ip": tcp.get("ip"),
            "country": None,
            "city": None,
            "flag": "",
            "isp": None,
            "latency_ms": int(tcp.get("latency_ms", 0) or 0),
            "tested_at": now_ts,
            "tested_at_tehran": jalali_datetime(now_ts),
            "healthy": bool(tcp.get("ok") and tcp.get("ip")),
            "queued": not bool(tcp.get("ok") and tcp.get("ip")),
        }
        if record["healthy"]:
            record.update(await geo_lookup(client, storage, str(record["ip"])))
        return config_id(uri), record
    finally:
        if owns_session:
            await client.close()


def format_test_card(record: dict[str, Any], iran_votes: dict[str, Any] | None = None) -> str:
    if isinstance(iran_votes, dict):
        ok = len(iran_votes.get("ok", []))
        fail = len(iran_votes.get("fail", []))
    else:
        ok = 0
        fail = 0
    return fa.test_card(
        protocol=str(record["protocol"]),
        host=str(record["host"]),
        port=int(record["port"]),
        ip=str(record["ip"]),
        country=record.get("country"),
        city=record.get("city"),
        flag=record.get("flag"),
        isp=record.get("isp"),
        latency_ms=int(record.get("latency_ms", 0)),
        tested_at=str(record["tested_at_tehran"]),
        data_remaining_gb=record.get("data_remaining_gb"),
        iran_ok=ok,
        iran_fail=fail,
    )


def make_qr_png(uri: str) -> BytesIO:
    image = qrcode.make(uri)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    output.name = "config_qr.png"
    return output
