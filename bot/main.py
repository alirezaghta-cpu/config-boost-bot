from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.handlers import (
    ActionRateMiddleware,
    AppContext,
    MembershipGateMiddleware,
    router,
)
from bot.storage import KVStorage

try:  # menu_fix is optional: never let it take the whole bot down
    from bot import menu_fix
except Exception as _menu_fix_import_error:  # noqa: BLE001
    menu_fix = None
    logging.getLogger(__name__).error(
        "menu_fix import failed: %s", _menu_fix_import_error
    )


async def run() -> None:
    settings = load_config()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    storage = KVStorage(
        settings.cloudflare_api_token,
        settings.cloudflare_account_id,
        settings.kv_namespace_id,
    )
    await storage.open()
    context = AppContext(settings=settings, storage=storage)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    router.message.outer_middleware(ActionRateMiddleware(storage))
    router.callback_query.outer_middleware(ActionRateMiddleware(storage))
    router.message.outer_middleware(MembershipGateMiddleware(context))
    router.callback_query.outer_middleware(MembershipGateMiddleware(context))
    if menu_fix is not None:
        try:
            menu_fix.install()
        except Exception as _menu_fix_install_error:  # noqa: BLE001
            logging.getLogger(__name__).error(
                "menu_fix install failed: %s", _menu_fix_install_error
            )
    dispatcher.include_router(router)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot, ctx=context)
    finally:
        await bot.session.close()
        await storage.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
