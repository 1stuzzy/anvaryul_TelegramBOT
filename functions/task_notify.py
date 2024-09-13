import asyncio
import aiohttp
from loguru import logger
from aiogram import Bot
from database.redis_base import RedisClient
from functions.wb_api import ApiClient
from loader import config


class NotificationService:
    def __init__(self, api_client: ApiClient, redis_client: RedisClient, bot: Bot, max_concurrent_requests=10, min_delay_between_requests=1.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests
        self.tasks = {}

    async def start_all_active_requests(self):
        """Запускает мониторинг для всех активных запросов из базы."""
        logger.info("Запуск мониторинга всех активных запросов из базы...")
        active_requests = await self.redis_client.get_all_active_requests()
        if not active_requests:
            logger.info("Нет активных запросов для мониторинга.")
            return

        for request in active_requests:
            user_id = request['user_id']
            request_id = request.get('request_id') or request['unique_id']
            logger.info(f"Запуск мониторинга для пользователя {user_id} по запросу {request_id}...")
            await self.start_search(user_id, request_id, request)

        logger.info("Все активные запросы успешно запущены для мониторинга.")

    async def start_search(self, user_id, request_id, request_data):
        """Запускает мониторинг для одного запроса."""
        stop_event = asyncio.Event()
        task = asyncio.create_task(self.process_requests(user_id, request_data, stop_event))
        self.tasks[request_id] = (task, stop_event)

    async def stop_search(self, user_id, request_id):
        """Останавливает мониторинг для одного запроса."""
        task, stop_event = self.tasks.pop(request_id, (None, None))
        if task:
            stop_event.set()
            await task

    async def process_requests(self, user_id, request_data, stop_event):
        """Процесс обработки запросов для конкретного пользователя."""
        try:
            params = {
                "boxTypeID": request_data["boxTypeID"],
                "warehouse_ids": request_data["warehouse_ids"],
                "coefficient": request_data["coefficient"]
            }

            async with aiohttp.ClientSession() as session:
                while not stop_event.is_set():
                    # Проверяем актуальный статус запроса перед отправкой нового запроса
                    current_request_status = await self.redis_client.get_request_status(user_id, request_data["request_id"])

                    # Если статус запроса False, прекращаем обработку
                    if not current_request_status:
                        logger.info(f"Запрос {request_data['request_id']} пользователя {user_id} остановлен.")
                        break

                    logger.debug(f"Отправка запроса для пользователя {user_id} с параметрами: {params}")
                    data = await self.api_client.get_coefficient(request_data["warehouse_ids"])
                    if data is None:
                        logger.error(f"Не удалось получить данные от API для пользователя {user_id}")
                        break  # Прекращаем обработку, если данные не получены

                    logger.debug(f"Получен ответ от API для пользователя {user_id}: {data}")
                    await self.process_response(user_id, data, request_data["warehouse_ids"], request_data["coefficient"])
                    await asyncio.sleep(self.min_delay_between_requests)
        except Exception as e:
            logger.error(f"Ошибка при обработке запросов для пользователя {user_id}: {e}")


    async def process_response(self, user_id, data, selected_warehouse_ids, max_coefficient):
        """Обработка ответа от API и отправка уведомлений пользователю."""
        logger.debug(f"Обработка ответа для пользователя {user_id}: {data}")
        if isinstance(data, list):
            max_coefficient = float(max_coefficient)
            for entry in data:
                # Преобразуем warehouseID в строку перед проверкой и проверяем коэффициент
                if str(entry["warehouseID"]) in selected_warehouse_ids:
                    # Проверяем, что коэффициент также преобразован в число перед сравнением
                    if entry["coefficient"] is not None and entry["coefficient"] >= 0 and float(entry["coefficient"]) <= max_coefficient:
                        message = f"🟢 Найдено совпадение: {entry}"
                        await self.send_notification(user_id, message)
                    else:
                        logger.debug(f"Коэффициент {entry['coefficient']} недопустим (либо отрицательный, либо превышает {max_coefficient}). Пропуск.")
                else:
                    logger.debug(f"Склад {entry['warehouseID']} не соответствует выбранным пользователем {selected_warehouse_ids}. Пропуск.")
        else:
            logger.error(f"Некорректный формат данных: {data}")


    async def send_notification(self, user_id, message):
        """Отправка уведомления пользователю."""
        try:
            await self.bot.send_message(user_id, message)
            logger.info(f"Уведомление отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
