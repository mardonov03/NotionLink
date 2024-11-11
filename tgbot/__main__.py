import asyncio
import logging
import betterlogging as bl
import orjson
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from tgbot.models.models import Users, Tokens
from tgbot import handlers
from tgbot.data import config
from database import create_pool, init_db


async def setup_logging():
    log_level = logging.INFO
    bl.basic_colorized_config(level=log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting bot")


async def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(handlers.setup())


async def setup_middlewares(dp: Dispatcher) -> None:
    pass


async def setup_aiogram(dp: Dispatcher) -> None:
    await setup_handlers(dp)
    await setup_middlewares(dp)


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    try:
        pool = await create_pool()
        token_model = Tokens(db_pool=pool)
        user_model = Users(db_pool=pool)

        dispatcher['db'] = pool
        dispatcher['usermodel'] = user_model
        dispatcher['tokenmodel'] = token_model

        await init_db(pool)
        await setup_aiogram(dispatcher)
        logging.info("Bot started")
    except Exception as e:
        logging.error(f'Error during startup: {e}')


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    try:
        await dispatcher['db'].close()
        await bot.session.close()
        await dispatcher.storage.close()
        logging.info("Bot shutdown")
    except Exception as e:
        logging.error(f'error542678: {e}')


async def main():
    try:
        await setup_logging()
        session = AiohttpSession(
            json_loads=orjson.loads,
        )

        bot = Bot(
            token=config.BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        storage = MemoryStorage()

        dp = Dispatcher(
            storage=storage,
        )

        dp.startup.register(aiogram_on_startup_polling)
        dp.shutdown.register(aiogram_on_shutdown_polling)

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f'error6247423: {e}')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f'error672456274: {e}')