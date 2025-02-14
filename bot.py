import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from database.engine import create_db, session_maker, drop_db
from handlers import admin_handler, user_hendler
from middlewares.db import DataBaseSession


load_dotenv()
ALLOWED_UPDATES = ['message', 'edited_message', 'callback_query']
TOKEN = os.getenv('API_TOKEN')

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)


async def on_startup():
    await drop_db()
    await create_db()


async def on_shutdown():
    print('bot shutdown')


async def main():
    dp = Dispatcher()
    dp.include_routers(admin_handler.router, user_hendler.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())
