from re import I
import threading

from aiogram import Dispatcher, executor
from loguru import logger

#from Package.models import connect, disconnect
from loader import config, dp
from utils.notify import on_startup_notify
from utils.logger_config import setup_logger


async def on_startup(dispatcher: Dispatcher):

    setup_logger(level="DEBUG")

    logger.info("Setuping handlers...")
    import handlers

    if config.notify:
        await on_startup_notify(dispatcher)


async def on_shutdown(_):
    logger.info('Bot Stopped!')


def main():
    executor.start_polling(
        dp,
        skip_updates=config.skip_updates,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        timeout=5,
    )


if __name__ == "__main__":
    main()
