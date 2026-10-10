from __future__ import annotations

import json
import secrets
import time
from datetime import timedelta
from typing import Any
from urllib.parse import quote

import aiohttp

from bot import quota
from bot.util import mask_secret, tehran_now

DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/config.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/all_configs.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Delta-Kronecker/V2ray-Config/main/All_Configs_Sub.txt",
]


class StorageError(RuntimeError):
    pass


class KVStorage:
    def __init__(
        self,
        api_token: str,
        account_id: str,
        namespace_id: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.api_token = api_token
        self.base_url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/storage/kv/namespaces/{namespace_id}"
        )
        self._session = session
        self._owns_session = session is None

    async def open(self) -> None:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
        self._session = None

    async def __aenter__(self) -> "KVStorage":
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise StorageError("KV session is not open")
        return self._session

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_token}"}

    def _safe_error(self, status: int, detail: str) -> StorageError:
        safe = detail.replace(self.api_token, mask_secret(self.api_token))
        return StorageError(f"Cloudflare KV HTTP {status}: {safe[:300]}")

    async def get_text(self, key: str) -> str | None:
        url = f"{self.base_url}/values/{quote(key, safe='')}"
        async with self.session.get(url, headers=self.headers) as response:
            if response.status == 404:
                return None
            if response.status >= 400:
                raise self._safe_error(response.status, await response.text())
            return await response.text()

    async def put_text(self, key: str, value: str) -> None:
        url = f"{self.base_url}/values/{quote(key, safe='')}"
        headers = {**self.headers, "Content-Type": "text/plain; charset=utf-8"}
        async with self.session.put(url, headers=headers, data=value.encode("utf-8")) as response:
            if response.status >= 400:
                raise self._safe_error(response.status, await response.text())

    async def delete(self, key: str) -> None:
        url = f"{self.base_url}/values/{quote(key, safe='')}"
        async with self.session.delete(url, headers=self.headers) as response:
            if response.status not in {200, 204, 404}:
                raise self._safe_error(response.status, await response.text())

    async def get_json(self, key: str, default: Any = None) -> Any:
        raw = await self.get_text(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError(f"Invalid JSON in KV key {key}") from exc

    async def put_json(self, key: str, value: Any) -> None:
        await self.put_text(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")))

    async def list_keys(self, prefix: str) -> list[str]:
        names: list[str] = []
        cursor: str | None = None
        while True:
            params: dict[str, str | int] = {"prefix": prefix, "limit": 1000}
            if cursor:
                params["cursor"] = cursor
            url = f"{self.base_url}/keys"
            async with self.session.get(url, headers=self.headers, params=params) as response:
                data = await response.json(content_type=None)
                if response.status >= 400 or not data.get("success", False):
                    raise self._safe_error(response.status, json.dumps(data, ensure_ascii=False))
            names.extend(item["name"] for item in data.get("result", []))
            cursor = (data.get("result_info") or {}).get("cursor")
            if not cursor:
                return names

    @staticmethod
    def _new_user(tg_id: int, code: str) -> dict[str, Any]:
        return {
            "tg_id": int(tg_id),
            "code": code,
            "started_at": None,
            "inviter": None,
            "invited_at": None,
            "used_week_key": quota.week_key(),
            "used_this_week": 0,
            "used_total": 0,
            "qualified_at": None,
            "delivered_config_ids": [],
            "delivered_this_week_ids": [],
            "test_last_24h": {},
            "test_day": None,
            "test_day_count": 0,
            "rl": {},
            "uri_cache": [],
        }

    @staticmethod
    def _purge_user_cache(user: dict[str, Any], now_ts: float | None = None) -> dict[str, Any]:
        now_ts = now_ts or time.time()
        updated = dict(user)
        updated["uri_cache"] = [
            item
            for item in updated.get("uri_cache", [])
            if now_ts - float(item.get("ts", 0)) <= 86400
        ]
        last_tests = updated.get("test_last_24h", {})
        if not isinstance(last_tests, dict):
            last_tests = {}
        updated["test_last_24h"] = {
            str(key): float(ts)
            for key, ts in last_tests.items()
            if now_ts - float(ts) <= 86400
        }
        return updated

    async def ensure_user(self, tg_id: int) -> dict[str, Any]:
        key = f"user:{int(tg_id)}"
        user = await self.get_json(key)
        if user is None:
            for _ in range(6):
                code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8]
                if not await self.get_text(f"refcode:{code}"):
                    user = self._new_user(tg_id, code)
                    await self.put_json(key, user)
                    await self.put_text(f"refcode:{code}", str(int(tg_id)))
                    return user
            raise StorageError("Could not allocate referral code")
        updated = self._purge_user_cache(user)
        updated = quota.reset_week_if_needed(updated)
        if updated != user:
            await self.put_json(key, updated)
        return updated

    async def save_user(self, user: dict[str, Any]) -> None:
        await self.put_json(f"user:{int(user['tg_id'])}", self._purge_user_cache(user))

    async def inviter_by_code(self, code: str) -> int | None:
        value = await self.get_text(f"refcode:{code}")
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None

    async def get_invite_day_count(self, inviter_id: int, day: str) -> int:
        value = await self.get_text(f"invitee:{int(inviter_id)}:{day}")
        try:
            return max(0, int(value or 0))
        except ValueError:
            return 0

    async def set_invite_day_count(self, inviter_id: int, day: str, count: int) -> None:
        await self.put_text(f"invitee:{int(inviter_id)}:{day}", str(max(0, count)))

    async def users(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for key in await self.list_keys("user:"):
            value = await self.get_json(key)
            if isinstance(value, dict):
                result.append(self._purge_user_cache(value))
        return result

    async def referrals(self, inviter_id: int) -> list[dict[str, Any]]:
        return [u for u in await self.users() if u.get("inviter") == int(inviter_id)]

    async def referral_stats(self, inviter_id: int) -> dict[str, int]:
        refs = await self.referrals(inviter_id)
        qualified = sum(1 for user in refs if quota.is_qualified_invitee(user))
        return {
            "total": len(refs),
            "qualified": qualified,
            "pending": len(refs) - qualified,
        }

    async def leaderboard(self, limit: int = 10) -> list[tuple[int, int]]:
        counts: dict[int, int] = {}
        for user in await self.users():
            inviter = user.get("inviter")
            if inviter is not None and quota.is_qualified_invitee(user):
                counts[int(inviter)] = counts.get(int(inviter), 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]

    async def check_rate(
        self,
        tg_id: int,
        bucket: str,
        limit: int,
        window_seconds: int,
        *,
        consume: bool = True,
    ) -> tuple[bool, int]:
        user = await self.ensure_user(tg_id)
        decision = quota.fixed_window_allow(
            user.get("rl"), bucket, limit, window_seconds, time.time(), consume=consume
        )
        user["rl"] = decision.counters
        await self.save_user(user)
        return decision.allowed, decision.retry_after

    async def claim_test_slot(
        self,
        tg_id: int,
        config_key: str | None = None,
        enforce_24h: bool = False,
    ) -> str:
        user = await self.ensure_user(tg_id)
        now = time.time()
        if enforce_24h and config_key:
            previous = float(user.get("test_last_24h", {}).get(config_key, 0))
            if now - previous < 86400:
                return "24h"

        day = quota.tehran_day_key()
        if user.get("test_day") != day:
            user["test_day"] = day
            user["test_day_count"] = 0
        if int(user.get("test_day_count", 0)) >= 3:
            return "daily"
        user["test_day_count"] = int(user.get("test_day_count", 0)) + 1
        if enforce_24h and config_key:
            last = dict(user.get("test_last_24h", {}))
            last[config_key] = now
            user["test_last_24h"] = last
        await self.save_user(user)
        return "ok"

    async def cache_uri(self, tg_id: int, cache_id: str, uri: str) -> None:
        user = await self.ensure_user(tg_id)
        cache = [
            item for item in user.get("uri_cache", []) if item.get("id") != cache_id
        ]
        cache.append({"id": cache_id, "uri": uri, "ts": time.time()})
        user["uri_cache"] = cache[-20:]
        await self.save_user(user)

    async def get_cached_uri(self, tg_id: int, cache_id: str) -> str | None:
        user = await self.ensure_user(tg_id)
        for item in user.get("uri_cache", []):
            if item.get("id") == cache_id:
                return str(item.get("uri", ""))
        return None

    async def save_config(self, config_id: str, record: dict[str, Any]) -> None:
        await self.put_json(f"config:{config_id}", record)

    async def get_config(self, config_id: str) -> dict[str, Any] | None:
        value = await self.get_json(f"config:{config_id}")
        return value if isinstance(value, dict) else None

    async def set_healthy_ids(self, ids: list[str]) -> None:
        await self.put_json("configs:healthy", list(dict.fromkeys(ids)))

    async def healthy_configs(self, max_age_days: int = 7) -> list[dict[str, Any]]:
        ids = await self.get_json("configs:healthy", [])
        if not isinstance(ids, list):
            ids = []
        cutoff = time.time() - timedelta(days=max_age_days).total_seconds()
        valid: list[dict[str, Any]] = []
        valid_ids: list[str] = []
        for config_id in ids:
            record = await self.get_config(str(config_id))
            if (
                record
                and record.get("healthy") is True
                and record.get("ip")
                and float(record.get("tested_at", 0)) >= cutoff
            ):
                record["id"] = str(config_id)
                valid.append(record)
                valid_ids.append(str(config_id))
        if valid_ids != ids:
            await self.set_healthy_ids(valid_ids)
        return valid

    async def add_healthy_id(self, config_id: str) -> None:
        ids = await self.get_json("configs:healthy", [])
        if not isinstance(ids, list):
            ids = []
        await self.set_healthy_ids([config_id, *ids])

    async def posted_at(self, config_id: str) -> float:
        value = await self.get_text(f"posted:{config_id}")
        try:
            return float(value or 0)
        except ValueError:
            return 0

    async def mark_posted(self, config_id: str, ts: float | None = None) -> None:
        await self.put_text(f"posted:{config_id}", str(ts or time.time()))

    async def get_post_mode(self) -> str:
        mode = (await self.get_text("post:mode") or "h5").strip()
        return mode if mode in {"h5", "weekly", "d3", "off"} else "h5"

    async def set_post_mode(self, mode: str) -> None:
        if mode not in {"h5", "weekly", "d3", "off"}:
            raise ValueError("invalid post mode")
        await self.put_text("post:mode", mode)

    async def get_iran_votes(self, config_id: int | str) -> dict[str, list[int]]:
        votes = await self.get_json(f"iran:{config_id}", None)
        if not isinstance(votes, dict):
            return {"ok": [], "fail": []}

        def _ints(value: object) -> list[int]:
            if not isinstance(value, list):
                return []
            out: list[int] = []
            for item in value:
                try:
                    out.append(int(item))
                except (TypeError, ValueError):
                    continue
            return out

        return {"ok": _ints(votes.get("ok")), "fail": _ints(votes.get("fail"))}

    async def record_iran_vote(self, config_id: int | str, tg_id: int | str, ok: bool) -> dict[str, list[int]]:
        votes = await self.get_iran_votes(config_id)
        tg = int(tg_id)
        votes["ok"] = [x for x in votes["ok"] if x != tg]
        votes["fail"] = [x for x in votes["fail"] if x != tg]
        if ok:
            votes["ok"].append(tg)
        else:
            votes["fail"].append(tg)
        await self.put_json(f"iran:{config_id}", votes)
        return votes

    async def get_auto_post(self) -> bool:
        return (await self.get_text("auto_post") or "on").strip() != "off"

    async def set_auto_post(self, enabled: bool) -> None:
        await self.put_text("auto_post", "on" if enabled else "off")

    async def get_sources(self) -> list[str]:
        sources = await self.get_json("sources", None)
        if not isinstance(sources, list):
            return list(DEFAULT_SOURCES)
        return [str(item) for item in sources if str(item).startswith("https://")]

    async def set_sources(self, sources: list[str]) -> None:
        cleaned = list(dict.fromkeys(item.strip() for item in sources if item.startswith("https://")))
        await self.put_json("sources", cleaned)

    async def get_last_post(self) -> dict[str, Any]:
        value = await self.get_json("last_post", {})
        return value if isinstance(value, dict) else {}

    async def set_last_post(self, value: dict[str, Any]) -> None:
        await self.put_json("last_post", value)

    async def acquire_lock(self, name: str, ttl_seconds: int = 3000) -> bool:
        key = f"lock:{name}"
        now = time.time()
        lock = await self.get_json(key, {})
        if isinstance(lock, dict) and now - float(lock.get("ts", 0)) < ttl_seconds:
            return False
        await self.put_json(key, {"ts": now, "expires_at": now + ttl_seconds})
        return True

    async def release_lock(self, name: str) -> None:
        await self.delete(f"lock:{name}")

    async def get_geo(self, ip: str) -> dict[str, Any] | None:
        value = await self.get_json(f"geo:{ip}", None)
        if not isinstance(value, dict):
            return None
        if time.time() - float(value.get("ts", 0)) > 86400:
            await self.delete(f"geo:{ip}")
            return None
        data = value.get("data")
        return data if isinstance(data, dict) else None

    async def set_geo(self, ip: str, data: dict[str, Any]) -> None:
        await self.put_json(f"geo:{ip}", {"ts": time.time(), "data": data})

    async def append_admin_log(self, event: dict[str, Any]) -> None:
        log = await self.get_json("admin_log", [])
        if not isinstance(log, list):
            log = []
        item = {"ts": time.time(), **event}
        await self.put_json("admin_log", [*log[-199:], item])
        if event.get("level") == "error":
            await self.put_json("last_error", item)

    async def get_admin_log(self) -> list[dict[str, Any]]:
        value = await self.get_json("admin_log", [])
        return value if isinstance(value, list) else []

    async def get_last_error(self) -> dict[str, Any]:
        value = await self.get_json("last_error", {})
        return value if isinstance(value, dict) else {}
