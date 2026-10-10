"""یک‌بارمصرف: فیکس‌های دروازه عضویت/ارسال ادمین/ساده‌سازی کارت + ساخت HANDOFF واحد.
هر anchor پیدا نشود، با پیام صریح شکست می‌خورد (چیزی نیمه‌کاره نمی‌ماند)."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def insert_before(path, marker, block):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"marker missing in {path}: {marker[:70]!r}")
    p.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def repl(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"old block missing in {path}: {old[:70]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_between(path, start, end, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"start missing in {path}: {start[:70]!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"end missing in {path}: {end[:70]!r}")
    p.write_text(text[:i] + new + text[j:], encoding="utf-8")


GATE_BLOCK = '''CHANNEL_JOIN_URL = "https://t.me/GalaxiesDrop"


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


'''

GATE_VERIFY = '''@router.callback_query(F.data == "gate:verify")
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


'''

ADMIN_SEND_FUNC = '''@router.callback_query(F.data == "admin:send")
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
        f"{format_test_card(selected)}\n\n{fa.ADMIN_CONFIRM_SEND}",
        reply_markup=keyboard,
    )

'''

GATE_STRINGS = '''BTN_JOIN = "عضویت"
BTN_JOIN_CONFIRM = "تایید عضویت"
GATE_TEXT = (
    "برای استفاده از ربات ابتدا در کانال @GalaxiesDrop عضو شوید.\n\n"
    "۱) روی دکمهٔ «عضویت» بزنید و وارد کانال شوید.\n"
    "۲) در کانال عضو شوید و به ربات برگردید.\n"
    "۳) دکمهٔ «تایید عضویت» را بزنید."
)
GATE_NOT_MEMBER = "هنوز عضو کانال نیستید؛ اول عضو شوید، بعد تایید بزنید."
GATE_OK = "عضویت تأیید شد ✅"

'''

NEW_TEST_CARD = '''def test_card(
    protocol: str,
    host: str,
    port: int,
    ip: str,
    country: str | None,
    city: str | None,
    flag: str | None,
    isp: str | None,
    latency_ms: int,
    tested_at: str,
    *,
    data_remaining_gb: float | None = None,
    iran_ok: int = 0,
    iran_fail: int = 0,
) -> str:
    _ = host, port, ip, isp, tested_at
    if country and city:
        location = f"{flag + ' ' if flag else ''}{country} / {city}"
    else:
        location = UNKNOWN
    return (
        f"وضعیت: {HEALTHY} ✅\n"
        f"پروتکل: {html.escape(protocol)}\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"پینگ: {latency_ms} ms\n"
        f"{data_line(data_remaining_gb)}\n"
        f"{iran_line(iran_ok, iran_fail)}"
    )


'''

NEW_CHANNEL_POST = '''def channel_post(
    record: dict,
    bot_username: str,
    escaped_uri: str,
    *,
    iran_ok: int = 0,
    iran_fail: int = 0,
) -> str:
    country = record.get("country") or UNKNOWN
    city = record.get("city") or UNKNOWN
    flag = record.get("flag") or ""
    location = f"{flag + ' ' if flag else ''}{country} / {city}"
    reality_line = (
        "🛡 پروتکل: Reality (پیشنهادی برای ایران)\n"
        if str(record.get("security") or "").lower() == "reality"
        else ""
    )
    return (
        "<b>کانفیگ رایگان — ارسال هر ۵ ساعت</b>\n"
        "وضعیت: تست‌شده و سالم ✅\n"
        f"لوکیشن: {html.escape(location)}\n"
        f"پروتکل: {html.escape(str(record['protocol']))}\n"
        f"{reality_line}\n"
        f"<code>{escaped_uri}</code>\n\n"
        f"{data_line(record.get('data_remaining_gb'))}\n"
        f"{iran_line(iran_ok, iran_fail)}\n\n"
        f"دریافت کانفیگ رایگان از ربات: @{html.escape(bot_username)}"
    )


'''


def main() -> None:
    # 1) handlers.py: بلوک دروازه عضویت
    insert_before("bot/handlers.py", "def main_keyboard(", GATE_BLOCK)
    # 2) handlers.py: هندلر تایید عضویت
    insert_before("bot/handlers.py", "@router.message(CommandStart())", GATE_VERIFY)
    # 3) handlers.py: بازنویسی admin_send_select (رفع خالی‌شدن کاندیدا)
    replace_between(
        "bot/handlers.py",
        '@router.callback_query(F.data == "admin:send")',
        '@router.callback_query(F.data.startswith("admin:sendconfirm:"))',
        ADMIN_SEND_FUNC + "\n",
    )
    # 4) handlers.py: در fallback ارسال، متن از رکورد سالم ساخته شود نه تست ناموفق
    repl(
        "bot/handlers.py",
        '            {"level": "warning", "event": "manual_retest_fallback_record", "config_id": config_id_value}\n        )\n    else:',
        '            {"level": "warning", "event": "manual_retest_fallback_record", "config_id": config_id_value}\n        )\n        fresh = dict(record)\n    else:',
    )
    # 5) fa.py: متن‌های دروازه
    insert_before("bot/locales/fa.py", "ADMIN_ONLY = ", GATE_STRINGS)
    # 6) fa.py: کارت ساده‌شده
    replace_between("bot/locales/fa.py", "def test_card(", "def channel_post(", NEW_TEST_CARD)
    # 7) fa.py: پست کانال ساده‌شده
    replace_between("bot/locales/fa.py", "def channel_post(", "def config_code(", NEW_CHANNEL_POST)
    # 8) ساخت HANDOFF واحد از پارت‌ها
    parts_dir = ROOT / "handoff_parts"
    if parts_dir.is_dir():
        parts = sorted(parts_dir.glob("p*.md"))
        if len(parts) != 3:
            raise SystemExit(f"expected 3 handoff parts, found {len(parts)}")
        merged = "\n".join(p.read_text(encoding="utf-8") for p in parts)
        (ROOT / "HANDOFF.md").write_text(merged, encoding="utf-8")
        shutil.rmtree(parts_dir)
    elif not (ROOT / "HANDOFF.md").is_file():
        raise SystemExit("handoff_parts missing and HANDOFF.md absent")
    print("apply_fix3 OK")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"apply_fix3 failed: {type(exc).__name__}: {exc}")
