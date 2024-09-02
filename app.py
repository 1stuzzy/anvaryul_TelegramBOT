import asyncio
from aiogram import Dispatcher, executor
from loguru import logger

from db.models import connect, disconnect
from loader import config, dp
from utils.notify import on_startup_notify
from utils.logger_config import setup_logger
from wb_api import process_notifications, init_redis, check_and_notify_users


async def on_startup(dispatcher: Dispatcher):
    global notification_task
    connect()

    setup_logger(level="DEBUG")

    logger.info("Setuping handlers...")
    import handlers

    if config.notify:
        await on_startup_notify(dispatcher)

    # Инициализация Redis
    redis = await init_redis()

    # Запуск процесса уведомлений
    notification_task = asyncio.create_task(process_notifications(redis))

    # Запуск регулярной проверки и уведомлений
    asyncio.create_task(check_and_notify_users(redis))


async def on_shutdown(_):
    global notification_task
    if notification_task:
        notification_task.cancel()  # Отменяем задачу
        await notification_task
    disconnect()
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
