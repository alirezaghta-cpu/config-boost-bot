"""منطق خالص سهمیه، ارجاع و محدودیت نرخ؛ بدون هیچ I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from bot.locales import fa

TEHRAN = ZoneInfo("Asia/Tehran")
BASE_WEEKLY_QUOTA = 1
MAX_NEW_INVITES_PER_DAY = 10


def _as_tehran(value: datetime | None = None) -> datetime:
    value = value or datetime.now(TEHRAN)
    if value.tzinfo is None:
        return value.replace(tzinfo=TEHRAN)
    return value.astimezone(TEHRAN)


def week_key(value: datetime | None = None) -> str:
    """تاریخ ISO شنبه‌ای را برمی‌گرداند که هفتهٔ تهران از آن آغاز شده است."""
    local = _as_tehran(value)
    days_since_saturday = (local.weekday() - 5) % 7
    return (local.date() - timedelta(days=days_since_saturday)).isoformat()


def tehran_day_key(value: datetime | None = None) -> str:
    return _as_tehran(value).date().isoformat()


def bonus_quota(qualified: int) -> int:
    return max(0, int(qualified)) // 2


def total_entitlement(qualified: int) -> int:
    return BASE_WEEKLY_QUOTA + bonus_quota(qualified)


def balance(qualified: int, used_this_week: int) -> int:
    return max(0, total_entitlement(qualified) - max(0, int(used_this_week)))


calculate_balance = balance


def reset_week_if_needed(user: dict[str, Any], value: datetime | None = None) -> dict[str, Any]:
    """یک کپی برمی‌گرداند؛ شمار معتبر و سابقهٔ کلی هرگز ریست نمی‌شود."""
    current = week_key(value)
    updated = dict(user)
    if updated.get("used_week_key") != current:
        updated["used_week_key"] = current
        updated["used_this_week"] = 0
        updated["delivered_this_week_ids"] = []
    else:
        updated["used_this_week"] = max(0, int(updated.get("used_this_week", 0)))
        updated["delivered_this_week_ids"] = list(updated.get("delivered_this_week_ids", []))
    updated["delivered_config_ids"] = list(updated.get("delivered_config_ids", []))
    return updated


def shortage_message(qualified: int, used_this_week: int) -> str:
    return fa.shortage(max(0, qualified), max(0, used_this_week))


@dataclass(frozen=True, slots=True)
class ReferralDecision:
    accepted: bool
    reason: str
    user: dict[str, Any]
    new_daily_count: int


def assign_referral(
    user: dict[str, Any],
    invitee_id: int,
    inviter_id: int,
    daily_new_count: int,
    value: datetime | None = None,
    *,
    first_start: bool = True,
) -> ReferralDecision:
    """قانون اولین دعوت‌کننده، خوددعوتی و سقف روزانه را اعمال می‌کند."""
    updated = dict(user)
    count = max(0, int(daily_new_count))
    if not first_start:
        return ReferralDecision(False, "not_first_start", updated, count)
    if int(invitee_id) == int(inviter_id):
        return ReferralDecision(False, "self_invite", updated, count)
    if updated.get("inviter") is not None:
        return ReferralDecision(False, "already_assigned", updated, count)
    if count >= MAX_NEW_INVITES_PER_DAY:
        return ReferralDecision(False, "daily_cap", updated, count)
    updated["inviter"] = int(inviter_id)
    updated["invited_at"] = _as_tehran(value).isoformat()
    updated["qualified_at"] = None
    return ReferralDecision(True, "accepted", updated, count + 1)


@dataclass(frozen=True, slots=True)
class ConsumptionResult:
    allowed: bool
    became_qualified: bool
    user: dict[str, Any]
    remaining: int


def consume_one(
    user: dict[str, Any],
    qualified_referrals: int,
    value: datetime | None = None,
    config_id: str | None = None,
) -> ConsumptionResult:
    updated = reset_week_if_needed(user, value)
    remaining = balance(qualified_referrals, int(updated.get("used_this_week", 0)))
    if remaining < 1:
        return ConsumptionResult(False, False, updated, 0)

    previous_total = max(0, int(updated.get("used_total", 0)))
    updated["used_this_week"] = int(updated.get("used_this_week", 0)) + 1
    updated["used_total"] = previous_total + 1
    if config_id:
        owned = list(dict.fromkeys([*updated.get("delivered_config_ids", []), config_id]))
        weekly = list(dict.fromkeys([*updated.get("delivered_this_week_ids", []), config_id]))
        updated["delivered_config_ids"] = owned
        updated["delivered_this_week_ids"] = weekly

    became_qualified = (
        previous_total == 0
        and updated.get("inviter") is not None
        and not updated.get("qualified_at")
    )
    if became_qualified:
        updated["qualified_at"] = _as_tehran(value).isoformat()

    return ConsumptionResult(
        True,
        became_qualified,
        updated,
        balance(qualified_referrals, updated["used_this_week"]),
    )


def is_qualified_invitee(user: dict[str, Any]) -> bool:
    return (
        user.get("inviter") is not None
        and max(0, int(user.get("used_total", 0))) >= 1
        and bool(user.get("qualified_at"))
    )


@dataclass(frozen=True, slots=True)
class RateDecision:
    allowed: bool
    counters: dict[str, dict[str, float | int]]
    retry_after: int


def fixed_window_allow(
    counters: dict[str, dict[str, float | int]] | None,
    bucket: str,
    limit: int,
    window_seconds: int,
    now_ts: float,
    *,
    consume: bool = True,
) -> RateDecision:
    """محدودکنندهٔ پنجرهٔ ثابت خالص برای ۱۵/دقیقه و ۲/ساعت."""
    updated = {key: dict(value) for key, value in (counters or {}).items()}
    state = updated.get(bucket, {})
    start = float(state.get("start", now_ts))
    count = int(state.get("count", 0))
    if now_ts - start >= window_seconds or now_ts < start:
        start, count = now_ts, 0
    if count >= limit:
        retry = max(1, int(window_seconds - (now_ts - start)))
        updated[bucket] = {"start": start, "count": count}
        return RateDecision(False, updated, retry)
    if consume:
        count += 1
    updated[bucket] = {"start": start, "count": count}
    return RateDecision(True, updated, 0)
