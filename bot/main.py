from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.handlers import ActionRateMiddleware, AppContext, router
from bot.storage import KVStorage


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
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    router.message.outer_middleware(ActionRateMiddleware(storage))
    router.callback_query.outer_middleware(ActionRateMiddleware(storage))
    dispatcher.include_router(router)
    context = AppContext(settings=settings, storage=storage)
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
