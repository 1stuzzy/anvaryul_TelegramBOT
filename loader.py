import asyncio

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode

from utils.config import load_config

"""
    bot settings:
        inline mode                         -   on
        allow groups                        -   on
        group privacy                       -   off
        admins chats   -   make bot admin!
"""

config = load_config()

storage = MemoryStorage()
bot = Bot(config.api_token, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
loop = asyncio.get_event_loop()
