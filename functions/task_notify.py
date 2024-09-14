from loguru import logger
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from functions.wb_api import ApiClient
from database.redis_base import RedisClient
from data import texts, keyboards
import asyncio
import hashlib
from datetime import datetime


class NotificationService:
    def __init__(self, api_client: ApiClient, redis_client: RedisClient, bot: Bot, scheduler: AsyncIOScheduler,
                 max_concurrent_requests=1, min_delay_between_requests=1.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.scheduler = scheduler
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests

    async def start_all_active_requests(self):
        """Запускает мониторинг для всех активных запросов из базы."""
        logger.info("Запуск мониторинга всех активных запросов из базы...")
        active_requests = await self.redis_client.get_all_active_requests()
        if not active_requests:
            logger.info("Нет активных запросов для мониторинга.")
            return

        tasks = [self.start_search(request['user_id'], request.get('request_id') or request['unique_id'], request)
                 for request in active_requests]
        await asyncio.gather(*tasks)
        logger.info("Все активные запросы успешно запущены для мониторинга.")

    async def start_search(self, user_id, request_id, request_data):
        """Запускает мониторинг для одного запроса."""
        interval = 5  # Интервал в секундах.
        self.scheduler.add_job(
            self.process_requests,
            'interval',
            seconds=interval,
            args=[user_id, request_data],
            id=request_id,
            replace_existing=True
        )
        logger.info(f"Запрос {request_id} для пользователя {user_id} запущен на мониторинг с интервалом {interval} секунд.")

    async def stop_search(self, user_id, request_id):
        """Останавливает мониторинг для одного запроса."""
        try:
            job = self.scheduler.get_job(request_id)
            if job:
                self.scheduler.remove_job(request_id)
                logger.info(f"Запрос {request_id} для пользователя {user_id} остановлен.")
            else:
                logger.warning(f"Задача с идентификатором {request_id} для пользователя {user_id} не найдена.")

            update_success = await self.redis_client.stop_request(user_id, request_id)

            if update_success:
                logger.info(f"Статус запроса {request_id} для пользователя {user_id} обновлен на False.")
            else:
                logger.error(f"Не удалось обновить статус запроса {request_id} для пользователя {user_id}.")

        except Exception as e:
            logger.error(f"Ошибка при попытке остановить запрос {request_id} для пользователя {user_id}: {e}")

    async def process_requests(self, user_id, request_data):
        """Процесс обработки запросов для конкретного пользователя."""
        async with self.semaphore:
            try:
                current_request_status = await self.redis_client.get_request_status(user_id, request_data["request_id"])

                if not current_request_status:
                    logger.info(f"Запрос {request_data['request_id']} для пользователя {user_id} остановлен из-за неактивного статуса.")
                    await self.stop_search(user_id, request_data["request_id"])
                    return

                logger.debug(f"Отправка запроса к API для пользователя {user_id} с параметрами: {request_data}")
                data = await self.api_client.get_coefficient(request_data["warehouse_ids"].split(','))

                if data is None:
                    logger.warning(f"Не удалось получить данные от API для пользователя {user_id}.")
                    return

                logger.debug(f"Получен ответ от API для пользователя {user_id}: {data}")
                await self.process_response(user_id, data, request_data)
                await asyncio.sleep(self.min_delay_between_requests)

            except Exception as e:
                logger.error(f"Ошибка при обработке запросов для пользователя {user_id}: {e}")

    async def process_response(self, user_id, data, request_data):
        """Обработка ответа от API и отправка уведомлений пользователю."""
        logger.debug(f"Начало обработки ответа для пользователя {user_id}. Данные: {data}")
        selected_warehouse_ids = request_data["warehouse_ids"].split(',')
        max_coefficient = float(request_data["coefficient"])

        sorted_entries = sorted(
            [entry for entry in data if str(entry["warehouseID"]) in selected_warehouse_ids],
            key=lambda x: (x["coefficient"], x["date"])
        )

        tasks = []
        for entry in sorted_entries:
            if entry["coefficient"] is not None and entry["coefficient"] >= 0 and float(entry["coefficient"]) <= max_coefficient:
                result_id = self.generate_result_id(user_id, entry)
                if await self.redis_client.is_notification_sent(result_id):
                    continue

                box_type_ids = request_data.get("boxTypeID", "").split(',')
                box_type_names = [name for name, (_, box_id) in texts.types_map.items() if str(box_id) in box_type_ids]

                date_str = entry.get("date", "Неизвестная дата")
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                except ValueError:
                    formatted_date = "Неизвестная дата"

                message = texts.alert_text.format(
                    date=formatted_date,
                    warehouseName=await self.redis_client.get_warehouse_name(entry["warehouseID"]),
                    boxTypeName=", ".join(box_type_names) if box_type_names else "Неизвестный тип",
                    coefficient=entry["coefficient"]
                )

                tasks.append(self.send_notification(user_id, message))
                await self.redis_client.mark_notification_as_sent(result_id)

        if tasks:
            await asyncio.gather(*tasks)
        else:
            logger.info(f"Нет уведомлений для отправки пользователю {user_id}.")

    def generate_result_id(self, user_id, entry):
        """Генерация уникального идентификатора для каждого результата."""
        result_string = f"{user_id}:{entry['warehouseID']}:{entry['coefficient']}"
        logger.debug(f"Генерация result_id для строки: {result_string}")
        return hashlib.sha256(result_string.encode()).hexdigest()

    async def send_notification(self, user_id, message):
        """Отправка уведомления пользователю."""
        try:
            await self.bot.send_message(user_id, message, reply_markup=keyboards.go_booking())
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
