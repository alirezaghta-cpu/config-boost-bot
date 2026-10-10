"""رفع باگ منوها: ضربه زدن روی دکمه‌های منوی اصلی در هر state ورودی فعال
نباید به ورودی کانفیگ تبدیل شود (پیام «فرمت کانفینگ معتبر نیست»).

این ماژول یک هندلر با اولویت بالاتر (position 0) جلوی همهٔ هندلرهای state
در router.message قرار می‌دهد: اگر متن یکی از دکمه‌های منوی اصلی باشد و
کاربر در هر state ورودی باشد، state پاک و هندلر منوی درست اجرا می‌شود.
"""

from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers import (
    AppContext,
    admin_panel,
    help_message,
    purchase,
    quota_status,
    receive_config,
    referral_status,
    router,
    support_prompt,
    test_prompt,
)
from bot.locales import fa

logger = logging.getLogger(__name__)

MENU_TEXTS: frozenset[str] = frozenset(
    {
        fa.BTN_RECEIVE,
        fa.BTN_TEST,
        fa.BTN_QUOTA,
        fa.BTN_REFERRAL,
        fa.BTN_BUY,
        fa.BTN_HELP,
        fa.BTN_SUPPORT,
        fa.BTN_ADMIN,
    }
)


async def _menu_escape_filter(event: object, **data: object) -> bool:
    if not isinstance(event, Message) or event.text not in MENU_TEXTS:
        return False
    state = data.get("state")
    if state is None:
        return False
    try:
        return bool(await state.get_state())
    except Exception:  # pragma: no cover - defensive
        return False


async def _menu_escape_handler(
    message: Message, state: FSMContext, ctx: AppContext
) -> None:
    await state.clear()
    text = message.text
    if text == fa.BTN_RECEIVE:
        await receive_config(message, ctx)
    elif text == fa.BTN_TEST:
        await test_prompt(message, state)
    elif text == fa.BTN_QUOTA:
        await quota_status(message, ctx)
    elif text == fa.BTN_REFERRAL:
        await referral_status(message, ctx)
    elif text == fa.BTN_BUY:
        await purchase(message)
    elif text == fa.BTN_HELP:
        await help_message(message)
    elif text == fa.BTN_SUPPORT:
        await support_prompt(message, state)
    elif text == fa.BTN_ADMIN:
        await admin_panel(message, ctx)
    else:
        logger.warning("menu_fix: unmapped menu text: %r", text)


def install() -> None:
    router.message.register(_menu_escape_handler, _menu_escape_filter)
    handlers = router.message.handlers
    if handlers:
        handlers.insert(0, handlers.pop())
    logger.info("menu_fix: menu-escape handler installed at position 0")
