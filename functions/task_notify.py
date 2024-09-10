import asyncio
from loguru import logger
from aiogram import Bot
from database.redis_base import RedisClient
from functions.wb_api import ApiClient
from utils.datefunc import datetime_local_now


class NotificationService:
    def __init__(self, api_client: ApiClient, redis_client: RedisClient, bot: Bot, max_concurrent_requests=10, min_delay_between_requests=1.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests
        self.tasks = {}

    async def start_user_task(self, user_id):
        """Запускает задачу для пользователя."""
        if user_id in self.tasks:
            logger.info(f"Задача для пользователя {user_id} уже запущена.")
            return

        self.tasks[user_id] = asyncio.create_task(self._process_user_requests(user_id))
        logger.info(f"Задача для пользователя {user_id} успешно запущена.")

    async def stop_user_task(self, user_id):
        """Останавливает задачу для пользователя."""
        if user_id in self.tasks:
            task = self.tasks[user_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Задача для пользователя {user_id} была успешно остановлена.")
            del self.tasks[user_id]

    async def _process_user_requests(self, user_id):
        """Процесс обработки запросов для конкретного пользователя."""
        while True:
            try:
                user_request = await self.redis_client.get_request_status(user_id)
                if not user_request:
                    logger.warning(f"Запрос для пользователя {user_id} не найден.")
                    await self.stop_user_task(user_id)
                    return

                coefficients = await self.api_client.get_coefficients(user_request['warehouse_ids'])
                if coefficients:
                    await self._notify_user(user_id, coefficients)
                await asyncio.sleep(self.min_delay_between_requests)

            except Exception as e:
                logger.error(f"Ошибка при обработке запросов для пользователя {user_id}: {e}")
                await asyncio.sleep(5)

    async def _notify_user(self, user_id, coefficients):
        """Отправляет уведомление пользователю."""
        message = f"Коэффициенты для вашего запроса: {coefficients}"
        await self.bot.send_message(user_id, message)

    async def save_request(self, user_id, warehouse_ids):
        """Запускает отслеживание коэффициентов для конкретного пользователя."""
        await self.redis_client.save_request(user_id, warehouse_ids)
        await self.start_user_task(user_id)

    async def stop_tracking(self, user_id):
        """Останавливает отслеживание коэффициентов для конкретного пользователя."""
        await self.redis_client.delete_request(user_id, datetime_local_now())
        await self.stop_user_task(user_id)
