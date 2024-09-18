from loguru import logger
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from functions.wb_api import ApiClient
from database.redis_base import RedisClient
import asyncio
from data import keyboards, texts
from datetime import datetime
import hashlib


class NotificationService:
    def __init__(self, api_client: ApiClient, redis_client: RedisClient, bot: Bot, scheduler: AsyncIOScheduler,
                 min_delay_between_requests=5):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.scheduler = scheduler
        self.min_delay_between_requests = min_delay_between_requests
        self.notification_delay = 60

    async def monitor_requests(self):
        """Метод для периодического мониторинга активных запросов."""
        try:
            active_requests = await self.redis_client.get_all_active_requests()
            if not active_requests:
                logger.info("Активные запросы отсутствуют.")
                return
            else:
                grouped_requests = self.group_requests_by_parameters(active_requests)
                tasks = [self.process_grouped_requests(group) for group in grouped_requests]
                await asyncio.gather(*tasks)
                logger.info("Обработка активных запросов завершена.")
        except Exception as e:
            logger.error(f"Ошибка в процессе мониторинга: {e}")

    def start_scheduler(self):
        """Запуск планировщика для фонового мониторинга запросов."""
        self.scheduler.add_job(self.monitor_requests, 'interval', seconds=self.min_delay_between_requests,
                               coalesce=True, max_instances=1)
        self.scheduler.start()

    def group_requests_by_parameters(self, requests):
        """Группирует запросы по общим параметрам, чтобы минимизировать количество запросов к API."""
        groups = {}
        for req in requests:
            key = (req['warehouse_ids'], req['coefficient'], tuple(str(req.get('boxTypeID', '')).split(',')))
            if key not in groups:
                groups[key] = []
            groups[key].append(req)
        return groups.values()

    async def process_grouped_requests(self, requests):
        """Обрабатывает сгруппированные запросы, отправляя один запрос к API на группу."""
        if not requests:
            return

        user_ids = [req['user_id'] for req in requests]

        try:
            logger.debug(f"Отправка запроса к API для пользователей {user_ids}")

            warehouse_ids = list(set(
                warehouse_id
                for req in requests
                for warehouse_id in self.safe_split(req['warehouse_ids'])
            ))
            data = await self.api_client.get_coefficient(warehouse_ids)

            if not data:
                logger.warning(f"Не удалось получить данные от API для пользователей {user_ids}.")
                return

            for request_data in requests:
                await self.handle_api_response(request_data['user_id'], data, request_data)

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса для пользователей {user_ids}: {e}")

    async def handle_api_response(self, user_id, data, request_data):
        """Обрабатывает ответ от API и отправляет уведомления пользователю."""
        logger.debug('Ответ API получен')

        selected_warehouses = set(self.safe_split(request_data["warehouse_ids"]))
        selected_box_types = set(self.safe_split(request_data.get("boxTypeID", "")))
        max_coefficient = float(request_data["coefficient"])

        relevant_entries = sorted(
            [
                entry for entry in data
                if str(entry.get("warehouseID")) in selected_warehouses
                   and 0 <= float(entry.get("coefficient", -1)) <= max_coefficient
                   and str(entry.get("boxTypeID", "")) in selected_box_types
            ],
            key=lambda x: (x["coefficient"], x["date"])
        )

        if not relevant_entries:
            logger.info(f"Нет уведомлений для отправки пользователю {user_id}.")
            return

        logger.debug(f"Найдены данные для отправки уведомления пользователю {user_id}: {relevant_entries}")

        for entry in relevant_entries:
            await self.send_notification_if_needed(user_id, entry)

    async def send_notification_if_needed(self, user_id, entry):
        """Отправляет уведомление пользователю, если с последней отправки похожего уведомления прошло достаточное время."""
        try:
            # Генерируем сообщение
            box_type_ids = self.safe_split(entry.get("boxTypeID", ""))
            box_type_names = self.get_box_type_names(box_type_ids)
            formatted_date = self.format_date(entry.get("date"))

            coefficient = entry["coefficient"]
            coefficient_text = f"{coefficient}" if int(coefficient) != 0 else "0"

            message = texts.alert_text.format(
                date=formatted_date,
                warehouseName=await self.redis_client.get_warehouse_name(entry["warehouseID"]),
                boxTypeName=", ".join(box_type_names) if box_type_names else "Неизвестный тип",
                coefficient=coefficient_text
            )

            # Генерируем уникальный идентификатор сообщения на основе его содержимого
            message_id = self.generate_message_id(user_id, message)

            # Проверяем, было ли уже отправлено похожее сообщение недавно
            if await self.is_similar_notification_recently_sent(message_id):
                logger.info(f"Похожее уведомление уже отправлено пользователю {user_id}. Пропускаем.")
                return

            # Отправляем уведомление
            await self.bot.send_message(user_id, message, reply_markup=keyboards.go_booking())
            logger.info(f"Уведомление отправлено пользователю {user_id}.")

            # Помечаем уведомление как отправленное
            await self.mark_notification_as_sent(message_id)

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

    async def is_similar_notification_recently_sent(self, message_id):
        """Проверяет, было ли похожее уведомление отправлено недавно."""
        return await self.redis_client.is_notification_sent(message_id)

    async def mark_notification_as_sent(self, message_id):
        """Помечает уведомление как отправленное с установленным временем жизни."""
        await self.redis_client.mark_notification_as_sent(message_id, self.notification_delay)

    def generate_message_id(self, user_id, message):
        """Генерирует уникальный идентификатор сообщения на основе пользователя и содержимого сообщения."""
        result_string = f"{user_id}:{message}"
        return hashlib.sha256(result_string.encode()).hexdigest()

    def get_box_type_names(self, box_type_ids):
        """Возвращает список названий типов коробок по их идентификаторам."""
        box_type_names = [
            name for name, (_, box_id) in texts.types_map.items() if str(box_id) in box_type_ids
        ]
        return box_type_names

    def safe_split(self, value, delimiter=','):
        """Безопасно разделяет строку по разделителю, если это строка."""
        if isinstance(value, str):
            return value.split(delimiter)
        elif isinstance(value, (int, float)):
            return [str(value)]
        elif isinstance(value, list):
            return [str(v) for v in value]
        else:
            return []

    def format_date(self, date_str):
        """Форматирует дату из строки в человекочитаемый вид."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return date_obj.strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            return "Неизвестная дата"

    async def stop_request_monitoring(self, user_id, request_id):
        """Останавливает мониторинг для одного запроса."""
        try:
            job = self.scheduler.get_job(request_id)
            if job:
                self.scheduler.remove_job(request_id)
                logger.info(f"Мониторинг запроса {request_id} для пользователя {user_id} остановлен.")
            else:
                logger.warning(f"Задача с идентификатором {request_id} не найдена для пользователя {user_id}.")

            # Обновляем статус запроса в Redis
            if await self.redis_client.stop_request(user_id, request_id):
                logger.info(f"Статус запроса {request_id} для пользователя {user_id} обновлен на неактивный.")
            else:
                logger.error(f"Не удалось обновить статус запроса {request_id} для пользователя {user_id}.")
        except Exception as e:
            logger.error(f"Ошибка при остановке запроса {request_id} для пользователя {user_id}: {e}")
