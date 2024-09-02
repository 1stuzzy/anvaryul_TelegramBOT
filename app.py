import asyncio
from aiogram import Dispatcher, executor
from loguru import logger

from loader import config, dp, bot
from utils.notify import on_startup_notify
from utils.logger_config import setup_logger
from wb_api import process_notifications, check_and_notify_users, save_warehouses_to_db
from db.basefunctional import init_redis

notification_task = None

async def on_startup(dispatcher: Dispatcher):
    global notification_task
    
    # Настройка логирования
    setup_logger(level="DEBUG")

    logger.info("Setting up handlers...")
    
    # Импорт обработчиков (handlers) после настройки
    import handlers

    # Уведомление о старте бота, если включено
    if config.notify:
        await on_startup_notify(dispatcher)

    # Сохранение данных складов в базу (предполагаем, что функция асинхронная)
    #await save_warehouses_to_db()

    # Инициализация подключения к Redis
    #redis = await init_redis()

    # Запуск задачи обработки уведомлений
    #notification_task = asyncio.create_task(process_notifications(redis))

    # Запуск регулярной проверки и отправки уведомлений
    #asyncio.create_task(check_and_notify_users(redis))
    asyncio.create_task(check_and_notify_users(bot))


async def on_shutdown(_):
    global notification_task
    
    # Остановка задачи уведомлений, если она была запущена
    if notification_task:
        notification_task.cancel()
        await notification_task

    logger.info('Bot Stopped!')

def main():
    # Запуск бота с polling
    executor.start_polling(
        dp,
        skip_updates=config.skip_updates,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        timeout=5,
    )


if __name__ == "__main__":
    main()
