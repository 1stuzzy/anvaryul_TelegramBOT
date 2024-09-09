import asyncio
from aiogram import Dispatcher, executor
from loader import config, dp
from loguru import logger
from db.models import connect, disconnect
from db.redis_base import RedisClient
from functions.task_notify import NotificationService
from functions.wb_api import ApiClient

async def on_startup(dispatcher: Dispatcher, loop):
    # Подключение к базе данных
    connect()

    # Настройка логирования
    from utils.logger_config import setup_logger
    setup_logger(level="DEBUG")

    # Уведомление о запуске бота
    from utils.notify import on_startup_notify
    if config.notify:
        await on_startup_notify(dp)

    # Инициализация Redis-клиента
    redis_client = RedisClient(redis_url='redis://localhost')
    await redis_client.init()

    if redis_client and redis_client.redis:
        logger.info("Redis client successfully initialized.")
    else:
        logger.error("Failed to initialize Redis client.")
        raise SystemExit("Cannot initialize Redis client")

    dispatcher.bot['redis_client'] = redis_client

    logger.info("Setting up handlers...")
    import handlers

    # Инициализация API-клиента и службы уведомлений
    api_client = ApiClient(api_key=config.api_key)
    notification_service = NotificationService(api_client=api_client,
                                               redis_client=redis_client,
                                               bot=dispatcher.bot)
    
    # Запуск фоновой задачи через loop
    loop.create_task(notification_service.check_and_notify_users())

async def on_shutdown(_):
    # Отключение от базы данных
    disconnect()
    logger.info('Bot Stopped!')

def main():
    loop = asyncio.new_event_loop()  # Используем новый event loop
    asyncio.set_event_loop(loop)  # Устанавливаем его как текущий

    executor.start_polling(
        dp,
        loop=loop,  # Передаем loop в start_polling
        skip_updates=config.skip_updates,
        on_startup=lambda dispatcher: on_startup(dispatcher, loop),
        on_shutdown=on_shutdown,
    )

if __name__ == "__main__":
    main()
