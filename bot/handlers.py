from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    TelegramObject,
)

from bot import quota
from bot.cards import ConfigParseError, format_test_card, inspect_uri, make_qr_png, parse_config_uri
from bot.config import Settings
from bot.locales import fa
from bot.storage import KVStorage
from bot.util import config_id, escape_code, jalali_datetime, redact_text

router = Router(name="config_boost")


@dataclass(slots=True)
class AppContext:
    settings: Settings
    storage: KVStorage


class Flow(StatesGroup):
    test_uri = State()
    support = State()
    admin_source_add = State()
    admin_source_remove = State()
    admin_config_add = State()
    admin_quota_lookup = State()
    admin_quota_edit = State()
    admin_ref_lookup = State()
    admin_testcfg = State()
    admin_test_send = State()


class ActionRateMiddleware(BaseMiddleware):
    def __init__(self, storage: KVStorage) -> None:
        self.storage = storage

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text is None and event.document is None:
            return None
        user = getattr(event, "from_user", None)
        if user is not None:
            allowed, _ = await self.storage.check_rate(user.id, "actions", 15, 60)
            if not allowed:
                if isinstance(event, CallbackQuery):
                    await event.answer(fa.RATE_LIMIT, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(fa.RATE_LIMIT)
                return None
        return await handler(event, data)


CHANNEL_JOIN_URL = "https://t.me/GalaxiesDrop"


def join_gate_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    link = (getattr(settings, "channel_link", "") or CHANNEL_JOIN_URL).strip()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=fa.BTN_JOIN, url=link)],
            [InlineKeyboardButton(text=fa.BTN_JOIN_CONFIRM, callback_data="gate:verify")],
        ]
    )


async def channel_member_status(bot: Any, ctx: AppContext, user_id: int) -> bool | None:
    """True=عضو، False=عضو نیست، None=بررسی ناموفق (اجازه عبور + لاگ)."""
    if bot is None:
        return None
    try:
        member = await bot.get_chat_member(ctx.settings.channel_id, int(user_id))
    except Exception as exc:
        logging.warning("membership check failed for %s: %s", user_id, type(exc).__name__)
        try:
            await ctx.storage.append_admin_log(
                {
                    "level": "warning",
                    "event": "gate_check_error",
                    "user": int(user_id),
                    "error": type(exc).__name__,
                }
            )
        except Exception:
            pass
        return None
    return str(getattr(member, "status", "")) in {
        "member",
        "administrator",
        "creator",
        "restricted",
    }


class MembershipGateMiddleware(BaseMiddleware):
    """هر فعالیت کاربر مشروط به عضویت کانال است؛ ادمین‌ها و دکمه تایید عضویت مستثنا."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        if user.id in self.ctx.settings.admin_ids:
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and str(event.data or "").startswith("gate:"):
            return await handler(event, data)
        bot = data.get("bot") or getattr(event, "bot", None)
        status = await channel_member_status(bot, self.ctx, user.id)
        if status is not False:
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer(fa.GATE_NOT_MEMBER, show_alert=True)
            try:
                if event.message is not None:
                    await event.message.answer(
                        fa.GATE_TEXT, reply_markup=join_gate_keyboard(self.ctx.settings)
                    )
            except Exception:
                pass
        elif isinstance(event, Message):
            await event.answer(
                fa.GATE_TEXT, reply_markup=join_gate_keyboard(self.ctx.settings)
            )
        return None


def main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=fa.BTN_RECEIVE), KeyboardButton(text=fa.BTN_TEST)],
        [KeyboardButton(text=fa.BTN_QUOTA), KeyboardButton(text=fa.BTN_REFERRAL)],
        [KeyboardButton(text=fa.BTN_BUY), KeyboardButton(text=fa.BTN_HELP)],
        [KeyboardButton(text=fa.BTN_SUPPORT)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=fa.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def config_keyboard(config_id_value: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.BTN_TEST, callback_data=f"cfg:test:{config_id_value}"),
                InlineKeyboardButton(text=fa.BTN_COPY, callback_data=f"cfg:copy:{config_id_value}"),
                InlineKeyboardButton(text=fa.BTN_QR, callback_data=f"cfg:qr:{config_id_value}"),
            ],
            [
                InlineKeyboardButton(
                    text=fa.BTN_IRAN_VOTE_OK,
                    callback_data=f"cfg:iran:{config_id_value}:ok",
                ),
                InlineKeyboardButton(
                    text=fa.BTN_IRAN_VOTE_FAIL,
                    callback_data=f"cfg:iran:{config_id_value}:fail",
                ),
            ],
        ]
    )


def channel_keyboard(settings: Settings, config_id_value: str) -> InlineKeyboardMarkup:
    link = f"https://t.me/{settings.bot_username}?start=cfg_{config_id_value}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.BTN_TEST, url=link),
                InlineKeyboardButton(text=fa.BTN_COPY_FROM_BOT, url=link),
            ]
        ]
    )


PRIORITY_COUNTRIES = ("DE", "FR", "NL", "CA", "US")
IRAN_TLS_PORTS = {8443, 2053, 2083, 2087, 2096, 80}


def _proto_port_score(record: dict) -> int:
    proto = str(record.get("protocol") or "").lower()
    sec = str(record.get("security") or "").lower()
    port = int(record.get("port") or 0)
    score = 0
    if proto == "vless" and sec == "reality":
        score += 60
    elif proto == "trojan":
        score += 45
    elif proto == "vless":
        score += 35
    elif proto == "vmess":
        score += 20
    else:
        score += 5
    if port == 443:
        score += 25
    elif port in IRAN_TLS_PORTS:
        score += 12
    return score


@router.callback_query(F.data.startswith("cfg:iran:"))
async def iran_vote(callback: CallbackQuery, ctx: AppContext) -> None:
    _prefix, _marker, config_id, verdict = callback.data.split(":", 3)
    record = await ctx.storage.get_config(config_id)
    if not record:
        await callback.answer(fa.CONFIG_NOT_FOUND, show_alert=True)
        return
    user = await ctx.storage.ensure_user(callback.from_user.id)
    if config_id not in user.get("delivered_config_ids", []):
        await callback.answer(fa.IRAN_VOTE_ONLY_DELIVERED, show_alert=True)
        return
    votes = await ctx.storage.record_iran_vote(
        config_id, callback.from_user.id, verdict == "ok"
    )
    await callback.answer(
        fa.IRAN_VOTE_OK_SAVED if verdict == "ok" else fa.IRAN_VOTE_FAIL_SAVED
    )
    await callback.message.answer(
        fa.iran_line(len(votes.get("ok", [])), len(votes.get("fail", [])))
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.ADMIN_STATUS_BTN, callback_data="admin:status"),
                InlineKeyboardButton(text=fa.ADMIN_SEND_BTN, callback_data="admin:send"),
            ],
            [
                InlineKeyboardButton(text=fa.ADMIN_MODE_BTN, callback_data="admin:modes"),
                InlineKeyboardButton(text=fa.ADMIN_SOURCES_BTN, callback_data="admin:sources"),
            ],
            [
                InlineKeyboardButton(text=fa.ADMIN_ADD_CONFIG_BTN, callback_data="admin:addconfig"),
                InlineKeyboardButton(text=fa.ADMIN_QUOTA_BTN, callback_data="admin:quota"),
            ],
            [
                InlineKeyboardButton(text=fa.ADMIN_REFS_BTN, callback_data="admin:refs"),
                InlineKeyboardButton(text=fa.ADMIN_AUTOPOST_BTN, callback_data="admin:autopost"),
            ],
            [
                InlineKeyboardButton(text=fa.BTN_TEST_IRAN, callback_data="admin:testcfg"),
                InlineKeyboardButton(text=fa.BTN_STATS, callback_data="admin:stats"),
            ],
            [
                InlineKeyboardButton(text=fa.BTN_PURGE, callback_data="admin:purge"),
            ],
        ]
    )


def _is_admin(user_id: int, ctx: AppContext) -> bool:
    return user_id in ctx.settings.admin_ids


async def _show_config(message: Message, config: dict[str, Any], config_id_value: str, preview: bool = False) -> None:
    prefix = f"{fa.START_PREVIEW}\n\n" if preview else ""
    await message.answer(
        prefix + format_test_card(config),
        reply_markup=config_keyboard(config_id_value),
    )
    await message.answer(fa.IRAN_REPORT_PROMPT)


async def _register_start(user_id: int, payload: str | None, ctx: AppContext) -> dict[str, Any]:
    storage = ctx.storage
    user = await storage.ensure_user(user_id)
    first_start = not bool(user.get("started_at"))

    if first_start and payload and payload.startswith("ref_"):
        code = payload[4:]
        inviter_id = await storage.inviter_by_code(code)
        if inviter_id is not None:
            day = quota.tehran_day_key()
            count = await storage.get_invite_day_count(inviter_id, day)
            decision = quota.assign_referral(user, user_id, inviter_id, count, first_start=True)
            user = decision.user
            if decision.accepted:
                await storage.set_invite_day_count(inviter_id, day, decision.new_daily_count)
            elif decision.reason in {"daily_cap", "self_invite"}:
                await storage.append_admin_log(
                    {
                        "level": "warning",
                        "event": decision.reason,
                        "inviter": inviter_id,
                        "invitee": user_id,
                    }
                )
    if first_start:
        user["started_at"] = datetime.now(quota.TEHRAN).isoformat()
        await storage.save_user(user)
    return user


@router.callback_query(F.data == "gate:verify")
async def gate_verify(callback: CallbackQuery, ctx: AppContext) -> None:
    status = await channel_member_status(
        getattr(callback, "bot", None), ctx, callback.from_user.id
    )
    if status is False:
        await callback.answer(fa.GATE_NOT_MEMBER, show_alert=True)
        return
    await callback.answer(fa.GATE_OK)
    await callback.message.answer(
        fa.WELCOME,
        reply_markup=main_keyboard(_is_admin(callback.from_user.id, ctx)),
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, ctx: AppContext) -> None:
    payload = command.args.strip() if command.args else None
    await _register_start(message.from_user.id, payload, ctx)
    if payload and payload.startswith("cfg_"):
        config_id_value = payload[4:]
        config = await ctx.storage.get_config(config_id_value)
        if config and config.get("healthy") and config.get("ip"):
            await _show_config(message, config, config_id_value, preview=True)
        else:
            await message.answer(fa.CONFIG_NOT_FOUND)
    await message.answer(
        fa.WELCOME,
        reply_markup=main_keyboard(_is_admin(message.from_user.id, ctx)),
    )


@router.message(F.text == fa.BTN_RECEIVE)
async def receive_config(message: Message, ctx: AppContext) -> None:
    storage = ctx.storage
    user = await storage.ensure_user(message.from_user.id)
    stats = await storage.referral_stats(message.from_user.id)
    remaining = quota.balance(stats["qualified"], int(user.get("used_this_week", 0)))
    weekly_ids = list(user.get("delivered_this_week_ids", []))

    if remaining < 1:
        if weekly_ids:
            for item_id in weekly_ids:
                record = await storage.get_config(item_id)
                if record and record.get("healthy") and record.get("ip"):
                    await _show_config(message, record, item_id)
            await message.answer(fa.CONFIG_RESENT)
        await message.answer(quota.shortage_message(stats["qualified"], int(user.get("used_this_week", 0))))
        return

    healthy = await storage.healthy_configs()
    candidates = [record for record in healthy if record["id"] not in weekly_ids] or healthy
    if not candidates:
        await message.answer(fa.NO_HEALTHY_CONFIG)
        return

    async def _safe_votes(record: dict[str, Any]) -> dict[str, list[Any]]:
        try:
            v = await ctx.storage.get_iran_votes(record["id"])
            return v if isinstance(v, dict) else {"ok": [], "fail": []}
        except Exception:
            return {"ok": [], "fail": []}

    def _sort_key(
        item: tuple[dict[str, Any], dict[str, list[Any]]]
    ) -> tuple[int, int, int, float]:
        record, votes = item
        priority_rank = 0 if str(record.get("country_code") or "") in PRIORITY_COUNTRIES else 1
        return (
            -_proto_port_score(record),
            priority_rank,
            -len(votes.get("ok", [])),
            random.random(),
        )

    paired: list[tuple[dict[str, Any], dict[str, list[Any]]]] = [
        (record, await _safe_votes(record)) for record in candidates
    ]
    paired.sort(key=_sort_key)
    selected = paired[0][0]

    result = quota.consume_one(user, stats["qualified"], config_id=selected["id"])
    if not result.allowed:
        await message.answer(quota.shortage_message(stats["qualified"], int(user.get("used_this_week", 0))))
        return
    await storage.save_user(result.user)
    if result.became_qualified:
        await storage.append_admin_log(
            {
                "level": "info",
                "event": "referral_qualified",
                "invitee": message.from_user.id,
                "inviter": result.user.get("inviter"),
            }
        )
    await message.answer(fa.CONFIG_DELIVERED)
    await _show_config(message, selected, selected["id"])


@router.message(F.text == fa.BTN_TEST)
async def test_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Flow.test_uri)
    await message.answer(fa.TEST_PROMPT)


async def _test_user_uri(message: Message, uri: str, ctx: AppContext, state: FSMContext | None = None) -> None:
    try:
        parse_config_uri(uri)
    except ConfigParseError:
        await message.answer(fa.INVALID_URI)
        return
    slot = await ctx.storage.claim_test_slot(message.from_user.id)
    if slot == "daily":
        await message.answer(fa.TEST_DAILY_LIMIT)
        return
    item_id = config_id(uri)
    await ctx.storage.cache_uri(message.from_user.id, item_id, uri)
    try:
        _, record = await inspect_uri(uri, ctx.settings, ctx.storage)
    except ConfigParseError:
        await message.answer(fa.INVALID_URI)
        return
    if not record.get("healthy") or not record.get("ip"):
        await message.answer(fa.CONFIG_TEST_FAILED)
        return
    await message.answer(format_test_card(record))
    if state is not None:
        await state.clear()


@router.message(Flow.test_uri, F.text)
async def test_uri_state(message: Message, state: FSMContext, ctx: AppContext) -> None:
    await _test_user_uri(message, message.text.strip(), ctx, state)


@router.callback_query(F.data.startswith("cfg:test:"))
async def retest_config(callback: CallbackQuery, ctx: AppContext) -> None:
    config_id_value = callback.data.rsplit(":", 1)[-1]
    record = await ctx.storage.get_config(config_id_value)
    if not record:
        await callback.answer(fa.CONFIG_NOT_FOUND, show_alert=True)
        return
    user = await ctx.storage.ensure_user(callback.from_user.id)
    if config_id_value not in user.get("delivered_config_ids", []):
        if not record.get("healthy") or not record.get("ip"):
            await callback.answer(fa.CONFIG_TEST_FAILED, show_alert=True)
            return
        await callback.answer()
        await callback.message.answer(format_test_card(record))
        return

    slot = await ctx.storage.claim_test_slot(
        callback.from_user.id, config_id_value, enforce_24h=True
    )
    if slot == "24h":
        await callback.answer(fa.TEST_24H_LIMIT, show_alert=True)
        if record.get("healthy") and record.get("ip"):
            await callback.message.answer(format_test_card(record))
        else:
            await callback.message.answer(fa.CONFIG_TEST_FAILED)
        return
    if slot == "daily":
        await callback.answer(fa.TEST_DAILY_LIMIT, show_alert=True)
        return

    _, fresh = await inspect_uri(record["uri"], ctx.settings, ctx.storage)
    await ctx.storage.save_config(config_id_value, fresh)
    if not fresh.get("healthy") or not fresh.get("ip"):
        await callback.answer(fa.CONFIG_TEST_FAILED, show_alert=True)
        return
    await ctx.storage.add_healthy_id(config_id_value)
    await callback.answer()
    await callback.message.answer(format_test_card(fresh))


@router.callback_query(F.data.startswith("cfg:copy:"))
async def copy_config(callback: CallbackQuery, ctx: AppContext) -> None:
    config_id_value = callback.data.rsplit(":", 1)[-1]
    user = await ctx.storage.ensure_user(callback.from_user.id)
    record = await ctx.storage.get_config(config_id_value)
    if not record:
        await callback.answer(fa.CONFIG_NOT_FOUND, show_alert=True)
        return
    if config_id_value not in user.get("delivered_config_ids", []):
        await callback.answer(fa.COPY_DENIED, show_alert=True)
        if record.get("healthy") and record.get("ip"):
            await callback.message.answer(format_test_card(record))
        return
    await callback.answer()
    await callback.message.answer(fa.config_code(escape_code(str(record["uri"]))))


@router.callback_query(F.data.startswith("cfg:qr:"))
async def qr_config(callback: CallbackQuery, ctx: AppContext) -> None:
    config_id_value = callback.data.rsplit(":", 1)[-1]
    user = await ctx.storage.ensure_user(callback.from_user.id)
    record = await ctx.storage.get_config(config_id_value)
    if not record:
        await callback.answer(fa.CONFIG_NOT_FOUND, show_alert=True)
        return
    if config_id_value not in user.get("delivered_config_ids", []):
        await callback.answer(fa.QR_DENIED, show_alert=True)
        return
    image = make_qr_png(str(record["uri"]))
    await callback.answer()
    await callback.message.answer_photo(
        BufferedInputFile(image.getvalue(), filename="config_qr.png"),
        caption=fa.QR_CAPTION,
    )


@router.message(F.text.regexp(r"^(vless|vmess|trojan|ss)://"))
async def test_uri_direct(message: Message, ctx: AppContext) -> None:
    await _test_user_uri(message, message.text.strip(), ctx)


@router.message(F.text == fa.BTN_QUOTA)
async def quota_status(message: Message, ctx: AppContext) -> None:
    user = await ctx.storage.ensure_user(message.from_user.id)
    stats = await ctx.storage.referral_stats(message.from_user.id)
    remaining = quota.balance(stats["qualified"], int(user.get("used_this_week", 0)))
    await message.answer(
        fa.quota_status(
            stats["qualified"],
            stats["pending"],
            int(user.get("used_this_week", 0)),
            remaining,
        )
    )


@router.message(F.text == fa.BTN_REFERRAL)
async def referral_status(message: Message, ctx: AppContext) -> None:
    user = await ctx.storage.ensure_user(message.from_user.id)
    stats = await ctx.storage.referral_stats(message.from_user.id)
    rows = await ctx.storage.leaderboard(10)
    board = (
        "\n".join(fa.leaderboard_row(index, tg_id, count) for index, (tg_id, count) in enumerate(rows, 1))
        or fa.LEADERBOARD_EMPTY
    )
    link = f"https://t.me/{ctx.settings.bot_username}?start=ref_{user['code']}"
    await message.answer(
        fa.referral_status(
            link,
            stats["total"],
            stats["qualified"],
            stats["pending"],
            board,
        )
    )


@router.message(F.text == fa.BTN_BUY)
async def purchase(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=fa.PLAN_LIGHT, callback_data="plan:soon")],
            [InlineKeyboardButton(text=fa.PLAN_STANDARD, callback_data="plan:soon")],
            [InlineKeyboardButton(text=fa.PLAN_PRO, callback_data="plan:soon")],
            [InlineKeyboardButton(text=fa.PLAN_FAIR, callback_data="plan:soon")],
            [InlineKeyboardButton(text=fa.PLAN_SERVER, callback_data="plan:soon")],
            [InlineKeyboardButton(text=fa.BTN_ORDERS, callback_data="plan:orders")],
        ]
    )
    await message.answer(fa.PURCHASE_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "plan:soon")
async def plan_soon(callback: CallbackQuery) -> None:
    await callback.answer(fa.BTN_SOON, show_alert=True)


@router.callback_query(F.data == "plan:orders")
async def plan_orders(callback: CallbackQuery) -> None:
    await callback.answer(fa.NOT_ORDERED, show_alert=True)


@router.message(F.text == fa.BTN_HELP)
async def help_message(message: Message) -> None:
    await message.answer(fa.HELP_TEXT)


@router.message(F.text == fa.BTN_SUPPORT)
async def support_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Flow.support)
    await message.answer(fa.SUPPORT_PROMPT)


@router.message(Flow.support)
async def support_relay(message: Message, state: FSMContext, ctx: AppContext) -> None:
    allowed, _ = await ctx.storage.check_rate(message.from_user.id, "support", 2, 3600)
    if not allowed:
        await message.answer(fa.SUPPORT_LIMIT)
        await state.clear()
        return
    if not ctx.settings.admin_ids:
        await message.answer(fa.NO_ADMIN)
        await state.clear()
        return
    await message.forward(ctx.settings.first_admin_id)
    await message.answer(fa.SUPPORT_SENT)
    await state.clear()


@router.message(F.text == fa.BTN_ADMIN)
async def admin_panel(message: Message, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    await message.answer(fa.ADMIN_PANEL, reply_markup=admin_keyboard())


async def _is_admin_callback(callback: CallbackQuery, ctx: AppContext) -> bool:
    if not _is_admin(callback.from_user.id, ctx):
        await callback.answer(fa.ADMIN_ONLY, show_alert=True)
        return False
    return True


async def _admin_callback(callback: CallbackQuery, ctx: AppContext) -> bool:
    return await _is_admin_callback(callback, ctx)


async def _pick_admin_test_config(ctx: AppContext, exclude: set) -> dict | None:
    healthy = await ctx.storage.healthy_configs()
    fresh = [r for r in healthy if str(r.get("id")) not in exclude]
    pool = fresh or healthy
    if not pool:
        return None

    def key(r):
        pr = 0 if str(r.get("country_code") or "") in PRIORITY_COUNTRIES else 1
        return (pr, -_proto_port_score(r), random.random())

    pool.sort(key=key)
    return pool[0]


def _admin_test_keyboard(record: dict) -> InlineKeyboardMarkup:
    config_id_value = str(record["id"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=fa.BTN_IRAN_OK,
                    callback_data=f"admin:tcfsend:{config_id_value}",
                ),
                InlineKeyboardButton(
                    text=fa.BTN_IRAN_FAIL,
                    callback_data=f"admin:tcffail:{config_id_value}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔁 کانفیگ بعدی",
                    callback_data="admin:testcfg",
                )
            ],
        ]
    )


@router.callback_query(F.data == "admin:status")
async def admin_status(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    healthy = await ctx.storage.healthy_configs()
    last_post = await ctx.storage.get_last_post()
    last_error = await ctx.storage.get_last_error()
    last_post_text = (
        jalali_datetime(float(last_post["ts"])) if last_post.get("ts") else fa.UNKNOWN
    )
    error_text = fa.ADMIN_ERROR_RECORDED if last_error else fa.ADMIN_LAST_ERROR_NONE
    await callback.answer()
    await callback.message.answer(fa.admin_status(last_post_text, len(healthy), error_text))


@router.callback_query(F.data == "admin:testcfg")
async def admin_test_config(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _is_admin_callback(callback, ctx):
        return
    seen = set(await ctx.storage.admin_test_seen())
    record = await _pick_admin_test_config(ctx, seen)
    if record is None:
        await callback.answer(fa.ADMIN_NO_CANDIDATE, show_alert=True)
        return
    await ctx.storage.mark_admin_test_seen(str(record["id"]))
    await callback.answer()
    await callback.message.answer(
        f"{fa.ADMIN_TEST_SENT}\n\n{format_test_card(record)}\n\n{fa.config_code(escape_code(str(record['uri'])))}",
        reply_markup=_admin_test_keyboard(record),
    )


@router.callback_query(F.data.startswith("admin:tcfsend:"))
async def admin_test_send(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _is_admin_callback(callback, ctx):
        return
    config_id_value = callback.data.rsplit(":", 1)[-1]
    await callback.answer()
    ok = await _manual_post(callback, ctx, config_id_value)
    await callback.message.answer(fa.ADMIN_SENT if ok else fa.ADMIN_SEND_FAILED)


@router.callback_query(F.data.startswith("admin:tcffail:"))
async def admin_test_fail(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _is_admin_callback(callback, ctx):
        return
    config_id_value = callback.data.rsplit(":", 1)[-1]
    await ctx.storage.mark_admin_test_seen(config_id_value)
    seen = set(await ctx.storage.admin_test_seen())
    await callback.answer(fa.ADMIN_IRAN_FAIL_SAVED)
    record = await _pick_admin_test_config(ctx, seen)
    if record is None:
        await callback.message.answer(fa.ADMIN_NO_CANDIDATE)
        return
    await ctx.storage.mark_admin_test_seen(str(record["id"]))
    await callback.message.answer(
        f"{fa.ADMIN_TEST_SENT}\n\n{format_test_card(record)}\n\n{fa.config_code(escape_code(str(record['uri'])))}",
        reply_markup=_admin_test_keyboard(record),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _is_admin_callback(callback, ctx):
        return
    healthy = await ctx.storage.healthy_configs()
    protocol_counts = Counter(
        str(record.get("protocol") or fa.UNKNOWN) for record in healthy
    )
    country_counts = Counter(
        str(record.get("country") or record.get("country_code") or fa.UNKNOWN)
        for record in healthy
    )
    queued = sum(1 for record in healthy if record.get("queued"))
    protocols = "، ".join(
        f"{name}: {fa.num(count)}" for name, count in protocol_counts.most_common()
    ) or fa.UNKNOWN
    countries = "، ".join(
        f"{name}: {fa.num(count)}" for name, count in country_counts.most_common(5)
    ) or fa.UNKNOWN
    last_post = await ctx.storage.get_last_post()
    last_post_text = (
        jalali_datetime(float(last_post["ts"])) if last_post.get("ts") else fa.UNKNOWN
    )
    await callback.answer()
    await callback.message.answer(
        fa.ADMIN_STATS_FMT.format(
            healthy=fa.num(len(healthy)),
            queued=fa.num(queued),
            protocols=protocols,
            countries=countries,
            last_post=last_post_text,
        )
    )


@router.callback_query(F.data == "admin:purge")
async def admin_purge(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _is_admin_callback(callback, ctx):
        return
    removed, kept = await ctx.storage.purge_unhealthy()
    await callback.answer()
    await callback.message.answer(
        fa.ADMIN_PURGED_FMT.format(removed=removed, kept=kept)
    )


async def _post_message_retry(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    try:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
    except TelegramRetryAfter as exc:
        await asyncio.sleep(float(exc.retry_after))
        await bot.send_message(chat_id, text, reply_markup=keyboard)


async def _manual_post(
    callback: CallbackQuery,
    ctx: AppContext,
    config_id_value: str,
) -> bool:
    record = await ctx.storage.get_config(config_id_value)
    if not record:
        return False
    fresh = {}
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
        fresh = dict(record)
    else:
        if fresh:
            await ctx.storage.save_config(config_id_value, fresh)
        await ctx.storage.append_admin_log(
            {"level": "error", "event": "manual_retest_failed", "config_id": config_id_value}
        )
        return False
    text = fa.channel_post(fresh, ctx.settings.bot_username, escape_code(fresh["uri"]))
    keyboard = channel_keyboard(ctx.settings, config_id_value)
    sent: list[int] = []
    errors: list[str] = []
    for chat_id in (ctx.settings.channel_id, ctx.settings.group_id):
        try:
            await _post_message_retry(callback.bot, chat_id, text, keyboard)
            sent.append(chat_id)
        except Exception as exc:
            errors.append(type(exc).__name__)
    if sent:
        now = time.time()
        await ctx.storage.mark_posted(config_id_value, now)
        await ctx.storage.set_last_post(
            {"ts": now, "config_id": config_id_value, "targets": sent, "manual": True}
        )
    if errors:
        await ctx.storage.append_admin_log(
            {
                "level": "error",
                "event": "manual_post_partial" if sent else "manual_post_failed",
                "config_id": config_id_value,
                "errors": errors,
            }
        )
    return bool(sent)


@router.callback_query(F.data == "admin:send")
async def admin_send_select(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    healthy = await ctx.storage.healthy_configs()
    if not healthy:
        await callback.answer(fa.ADMIN_NO_CANDIDATE, show_alert=True)
        return
    candidates = []
    for record in healthy:
        if time.time() - await ctx.storage.posted_at(record["id"]) >= 7 * 86400:
            candidates.append(record)
    if not candidates:
        # استثناي مسير ادمين: قانون ۷ روزه بی‌اثر است؛ کهنه‌ترین ارسال‌شده انتخاب می‌شود
        posted = []
        for record in healthy:
            posted.append((await ctx.storage.posted_at(record["id"]), record))
        posted.sort(key=lambda item: item[0])
        candidates = [record for _, record in posted]
    selected = random.choice(candidates)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=fa.BTN_CONFIRM,
                    callback_data=f"admin:sendconfirm:{selected['id']}",
                ),
                InlineKeyboardButton(text=fa.BTN_CANCEL, callback_data="admin:cancel"),
            ]
        ]
    )
    await callback.answer()
    await callback.message.answer(
        f"{format_test_card(selected)}\n\n{fa.config_code(escape_code(str(selected['uri'])))}\n\n{fa.ADMIN_CONFIRM_SEND}",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("admin:sendconfirm:"))
async def admin_send_confirm(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    config_id_value = callback.data.rsplit(":", 1)[-1]
    await callback.answer()
    ok = await _manual_post(callback, ctx, config_id_value)
    await callback.message.answer(fa.ADMIN_SENT if ok else fa.ADMIN_SEND_FAILED)


@router.callback_query(F.data == "admin:modes")
async def admin_modes(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.ADMIN_MODE_WEEKLY, callback_data="admin:mode:weekly"),
                InlineKeyboardButton(text=fa.ADMIN_MODE_D3, callback_data="admin:mode:d3"),
                InlineKeyboardButton(text=fa.ADMIN_MODE_OFF, callback_data="admin:mode:off"),
            ],
            [InlineKeyboardButton(text=fa.ADMIN_MODE_H5, callback_data="admin:mode:h5")],
            [InlineKeyboardButton(text=fa.ADMIN_SEND_BTN, callback_data="admin:send")],
        ]
    )
    await callback.answer()
    await callback.message.answer(fa.ADMIN_MODE_BTN, reply_markup=keyboard)


@router.callback_query(F.data.startswith("admin:mode:"))
async def admin_mode_set(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    mode = callback.data.rsplit(":", 1)[-1]
    labels = {
        "weekly": fa.ADMIN_MODE_WEEKLY,
        "d3": fa.ADMIN_MODE_D3,
        "off": fa.ADMIN_MODE_OFF,
        "h5": fa.ADMIN_MODE_H5,
    }
    if mode not in labels:
        await callback.answer(fa.GENERIC_ERROR, show_alert=True)
        return
    await ctx.storage.set_post_mode(mode)
    await callback.answer()
    await callback.message.answer(fa.admin_mode_set(labels[mode]))


@router.callback_query(F.data == "admin:sources")
async def admin_sources(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    sources = await ctx.storage.get_sources()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.ADMIN_SOURCE_ADD, callback_data="admin:source:add"),
                InlineKeyboardButton(text=fa.ADMIN_SOURCE_REMOVE, callback_data="admin:source:remove"),
            ]
        ]
    )
    await callback.answer()
    await callback.message.answer(fa.sources_list(sources), reply_markup=keyboard)


@router.callback_query(F.data == "admin:source:add")
async def admin_source_add_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.set_state(Flow.admin_source_add)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_SOURCE)


@router.message(Flow.admin_source_add, F.text)
async def admin_source_add(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    source = message.text.strip()
    if not source.startswith("https://"):
        await message.answer(fa.ADMIN_SOURCE_INVALID)
        return
    sources = await ctx.storage.get_sources()
    await ctx.storage.set_sources([*sources, source])
    await state.clear()
    await message.answer(fa.ADMIN_SOURCE_ADDED)


@router.callback_query(F.data == "admin:source:remove")
async def admin_source_remove_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.set_state(Flow.admin_source_remove)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_SOURCE)


@router.message(Flow.admin_source_remove, F.text)
async def admin_source_remove(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    source = message.text.strip()
    sources = await ctx.storage.get_sources()
    if source not in sources:
        await message.answer(fa.ADMIN_SOURCE_NOT_FOUND)
        return
    await ctx.storage.set_sources([item for item in sources if item != source])
    await state.clear()
    await message.answer(fa.ADMIN_SOURCE_REMOVED)


@router.callback_query(F.data == "admin:addconfig")
async def admin_add_config_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.set_state(Flow.admin_config_add)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_CONFIG)


@router.message(Flow.admin_config_add, F.text)
async def admin_add_config(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    uri = message.text.strip()
    try:
        item_id, record = await inspect_uri(uri, ctx.settings, ctx.storage)
    except ConfigParseError:
        await message.answer(fa.INVALID_URI)
        return
    record["queued"] = not bool(record.get("healthy") and record.get("ip"))
    await ctx.storage.save_config(item_id, record)
    if record.get("healthy") and record.get("ip"):
        await ctx.storage.add_healthy_id(item_id)
        result = fa.ADMIN_CONFIG_HEALTHY
    else:
        result = fa.ADMIN_CONFIG_QUEUED
    await state.clear()
    await message.answer(result)


@router.callback_query(F.data == "admin:quota")
async def admin_quota_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.set_state(Flow.admin_quota_lookup)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_TGID)


@router.message(Flow.admin_quota_lookup, F.text)
async def admin_quota_lookup(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer(fa.ADMIN_BAD_NUMBER)
        return
    user = await ctx.storage.ensure_user(tg_id)
    stats = await ctx.storage.referral_stats(tg_id)
    remaining = quota.balance(stats["qualified"], int(user.get("used_this_week", 0)))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=fa.ADMIN_QUOTA_BTN, callback_data=f"admin:quotaedit:{tg_id}")]
        ]
    )
    await state.clear()
    await message.answer(
        fa.admin_user_quota(
            tg_id,
            stats["qualified"],
            stats["pending"],
            int(user.get("used_this_week", 0)),
            remaining,
        ),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("admin:quotaedit:"))
async def admin_quota_edit_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    tg_id = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(edit_tg_id=tg_id)
    await state.set_state(Flow.admin_quota_edit)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_USED)


@router.message(Flow.admin_quota_edit, F.text)
async def admin_quota_edit_value(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    data = await state.get_data()
    try:
        pieces = message.text.split()
        if len(pieces) == 1:
            tg_id = int(data["edit_tg_id"])
            used = int(pieces[0])
        else:
            tg_id, used = int(pieces[0]), int(pieces[1])
        if used < 0:
            raise ValueError
    except (ValueError, KeyError):
        await message.answer(fa.ADMIN_BAD_NUMBER)
        return
    await state.update_data(edit_tg_id=tg_id, edit_used=used)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fa.BTN_CONFIRM, callback_data="admin:quotaeditconfirm"),
                InlineKeyboardButton(text=fa.BTN_CANCEL, callback_data="admin:cancel"),
            ]
        ]
    )
    await message.answer(fa.ADMIN_CONFIRM_EDIT, reply_markup=keyboard)


@router.callback_query(F.data == "admin:quotaeditconfirm")
async def admin_quota_edit_confirm(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    data = await state.get_data()
    try:
        tg_id = int(data["edit_tg_id"])
        used = int(data["edit_used"])
    except (KeyError, ValueError, TypeError):
        await callback.answer(fa.GENERIC_ERROR, show_alert=True)
        return
    user = await ctx.storage.ensure_user(tg_id)
    user["used_this_week"] = used
    user["used_week_key"] = quota.week_key()
    await ctx.storage.save_user(user)
    await state.clear()
    await callback.answer()
    await callback.message.answer(fa.ADMIN_EDITED)


@router.callback_query(F.data == "admin:refs")
async def admin_refs_prompt(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.set_state(Flow.admin_ref_lookup)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_ASK_TGID)


@router.message(Flow.admin_ref_lookup, F.text)
async def admin_refs_view(message: Message, state: FSMContext, ctx: AppContext) -> None:
    if not _is_admin(message.from_user.id, ctx):
        await message.answer(fa.ADMIN_ONLY)
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer(fa.ADMIN_BAD_NUMBER)
        return
    referrals = await ctx.storage.referrals(tg_id)
    qualified_count = sum(1 for user in referrals if quota.is_qualified_invitee(user))
    details = "\n".join(
        fa.admin_referral_row(
            int(user.get("tg_id", 0)),
            quota.is_qualified_invitee(user),
        )
        for user in referrals[:100]
    )
    await state.clear()
    await message.answer(
        fa.admin_referrals(
            tg_id,
            len(referrals),
            qualified_count,
            len(referrals) - qualified_count,
            details,
        )
    )


@router.callback_query(F.data == "admin:autopost")
async def admin_autopost(callback: CallbackQuery, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    enabled = not await ctx.storage.get_auto_post()
    await ctx.storage.set_auto_post(enabled)
    await callback.answer()
    await callback.message.answer(fa.ADMIN_AUTOPOST_ON if enabled else fa.ADMIN_AUTOPOST_OFF)


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext, ctx: AppContext) -> None:
    if not await _admin_callback(callback, ctx):
        return
    await state.clear()
    await callback.answer()
    await callback.message.answer(fa.ADMIN_CANCELLED)


@router.error()
async def global_error(event: ErrorEvent, ctx: AppContext) -> bool:
    safe = redact_text(event.exception, ctx.settings.secret_values())
    logging.error("Unhandled bot error: %s", safe)
    try:
        await ctx.storage.append_admin_log(
            {"level": "error", "event": "bot_exception", "message": safe[:500]}
        )
    except Exception as storage_error:
        logging.error(
            "Could not write admin log: %s",
            redact_text(storage_error, ctx.settings.secret_values()),
        )
    try:
        update = event.update
        if update.message:
            await update.message.answer(fa.GENERIC_ERROR)
        elif update.callback_query:
            await update.callback_query.answer(fa.GENERIC_ERROR, show_alert=True)
    except Exception as notify_error:
        logging.error(
            "Could not notify user: %s",
            redact_text(notify_error, ctx.settings.secret_values()),
        )
    return True
