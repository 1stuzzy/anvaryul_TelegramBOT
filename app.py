from aiogram import Dispatcher, executor
from loguru import logger
from loader import config, dp
from database.models import connect, disconnect
from database.redis_base import RedisClient
from functions.task_notify import NotificationService
from functions.wb_api import ApiClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import handlers
from functions.executional import check_subscriptions


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

    api_client = ApiClient(api_keys=config.api_key, max_retries=5, retry_delay=2, rate_limit=5)
    scheduler = AsyncIOScheduler()
    notification_service = NotificationService(api_client=api_client,
                                               redis_client=redis_client,
                                               bot=dispatcher.bot,
                                               scheduler=scheduler)

    dispatcher.bot['notification_service'] = notification_service

    scheduler.add_job(check_subscriptions, 'interval', minutes=1)
    logger.info("Scheduler job for check_subscriptions added.")

    notification_service.start_scheduler()


async def on_shutdown(dispatcher: Dispatcher):
    disconnect()
    logger.info('Bot Stopped!')


def start_bot():
    executor.start_polling(
        dp,
        skip_updates=config.skip_updates,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )


def main():
    start_bot()


if __name__ == "__main__":
    main()
