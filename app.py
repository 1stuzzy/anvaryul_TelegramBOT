import asyncio
from aiogram import Dispatcher, executor
from loader import config, dp
from loguru import logger
from data.redis_base import RedisClient
from functions.task_notify import NotificationService
from functions.wb_api import ApiClient


async def on_startup(dispatcher: Dispatcher):

    from utils.logger_config import setup_logger
    setup_logger(level="DEBUG")

    from utils.notify import on_startup_notify
    if config.notify:
        await on_startup_notify(dp)

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

    api_client = ApiClient(api_key=config.api_key)

    #await RedisClient.upload_warehouses(api_client, redis_client)

    notification_service = NotificationService(api_client=api_client,
                                               redis_client=redis_client,
                                               tokens=config.api_key,
                                               bot=dispatcher.bot)
    asyncio.create_task(notification_service.check_and_notify_users())


async def on_shutdown(_):
    logger.info('Bot Stopped!')


def main():
    executor.start_polling(
        dp,
        skip_updates=config.skip_updates,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )


if __name__ == "__main__":
    main()
