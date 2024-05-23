import asyncio
import logging
import sys

from typing import Any

from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage, RedisEventIsolation

from utils.logger import setup_logger

from aiogram.client.default import DefaultBotProperties

from enums import Language

from redis.asyncio import Redis

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore

from aiogram_dialog import setup_dialogs

from settings import settings

from utils.redis_manager import RedisManager

from routers import router
from middlewares.db import DataBaseSession
from database.engine import create_db, async_session, drop_db

redis: "Redis[Any]" = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
)

core = FluentRuntimeCore(path='locales/{locale}/LC_MESSAGES')
manager = RedisManager(redis, settings.DEFAULT_LOCALE)


async def main():
    #await drop_db()
    await create_db()

    key_builder = DefaultKeyBuilder(with_destiny=True)
    storage = RedisStorage(redis=redis, key_builder=key_builder)
    events_isolation = RedisEventIsolation(redis=redis, key_builder=key_builder)

    bot = Bot(token=settings.TOKEN.get_secret_value(),
              default=DefaultBotProperties(parse_mode=ParseMode.HTML)
              )

    await bot.delete_webhook()


    dp = Dispatcher(storage=storage, event_isolation=events_isolation)

    setup_dialogs(dp)

    i18n_middleware = I18nMiddleware(
        core=core,
        manager=manager,
        locale_key="locale",
        default_locale=Language.EN,
    )

    i18n_middleware.setup(dp)

    dp.update.middleware(DataBaseSession(session_pool=async_session))

    dp.include_router(router)

    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == '__main__':
    try:
        setup_logger()
        asyncio.run(main())
    except KeyboardInterrupt or SystemExit:
        print('Exit')
