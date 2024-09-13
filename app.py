import multiprocessing
import asyncio
import handlers
from aiogram import Dispatcher, executor
from loguru import logger
from loader import config, dp
from database.models import connect, disconnect
from database.redis_base import RedisClient
from functions.task_notify import NotificationService
from functions.wb_api import ApiClient


def start_flask_app():
    handlers.app.run(host='0.0.0.0', port=5000)


async def on_startup(dispatcher: Dispatcher):
    connect()
    redis_client = RedisClient(redis_url=config.redis_url)
    await redis_client.init()
    dispatcher.bot['redis_client'] = redis_client

    from utils.logger_config import setup_logger
    setup_logger(level="DEBUG")

    if config.notify:
        from utils.notify import on_startup_notify
        await on_startup_notify(dispatcher)

    logger.info("Setting up handlers...")
    handlers.register_all_handlers(dispatcher)

    api_client = ApiClient(api_key=config.default_key)
    notification_service = NotificationService(api_client=api_client,
                                               redis_client=redis_client,
                                               bot=dispatcher.bot)

    dispatcher.bot['notification_service'] = notification_service

    #await notification_service.start_all_active_requests()


async def on_shutdown(dispatcher: Dispatcher):
    disconnect()
    logger.info('Bot Stopped!')


def main():
    flask_process = multiprocessing.Process(target=start_flask_app)
    flask_process.start()

    executor.start_polling(
        dp,
        skip_updates=config.skip_updates,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )

    # Останавливаем Flask-приложение при завершении работы бота
    flask_process.join()


if __name__ == "__main__":
    main()
