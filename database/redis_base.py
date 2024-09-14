import aioredis
import uuid

from datetime import datetime
from loguru import logger
from loader import config


class RedisClient:
    def __init__(self, redis_url=config.redis_url):
        self.redis_url = redis_url
        self.redis = None

    async def init(self):
        """Инициализация подключения к Redis."""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def ensure_connection(self):
        if self.redis is None:
            await self.init()

    async def save_request(self, user_id, warehouse_ids, boxTypeID, coefficient, start_date, end_date, status_request=True, notify_until_first=False):
        await self.ensure_connection()
        unique_id = await self.redis.incr(f"user_request:{user_id}")
        key = f"user_request:{user_id}:{unique_id}"

        request_data = {
            "request_id": str(unique_id),
            "user_id": str(user_id),
            "status_request": str(status_request),
            "warehouse_ids": ",".join(map(str, warehouse_ids)),
            "boxTypeID": boxTypeID,
            "coefficient": coefficient,
            "start_date": start_date,
            "end_date": end_date,
            "notify_until_first": str(notify_until_first)
        }

        try:
            await self.redis.hmset(key, mapping=request_data)
            await self.redis.save()
        except Exception as e:
            logger.exception(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")

    async def get_user_requests(self, user_id):
        await self.ensure_connection()
        try:
            keys_pattern = f"user_request:{user_id}:*"
            keys = await self.redis.keys(keys_pattern)

            user_requests = []

            for key in keys:
                request_data = await self.redis.hgetall(key)
                if request_data and request_data.get("user_id") == str(user_id):
                    user_requests.append(request_data)

            return user_requests
        except Exception as e:
            logger.exception(f"Ошибка при извлечении запросов пользователя {user_id}: {e}")
            return []

    async def get_warehouse_name(self, warehouse_id):
        await self.ensure_connection()
        """Получает имя склада по его идентификатору."""
        warehouse = await self.get_warehouse_by_id(warehouse_id)
        return warehouse.get('name', 'Неизвестный склад') if warehouse else 'Неизвестный склад'

    async def get_requests_list(self):
        await self.ensure_connection()
        """Получает все активные запросы пользователей из Redis."""
        try:
            keys = await self.redis.keys('user_request:*')
            user_requests = []
            for key in keys:
                request_data = await self.redis.hgetall(key)
                if request_data:
                    user_requests.append(request_data)
            return user_requests
        except Exception as e:
            logger.exception(f"Ошибка при получении запросов пользователей: {e}")
            return []

    async def update_coefficient(self, user_id, new_coefficient):
        await self.ensure_connection()
        """Обновляет коэффициент пользователя."""
        try:
            await self.redis.hset("user:coefficients", user_id, new_coefficient)
            logger.info(f"Коэффициент для пользователя с ID {user_id} обновлен на {new_coefficient}")
        except Exception as e:
            logger.exception(f"Не удалось обновить коэффициент для пользователя с ID {user_id}: {str(e)}")

    async def get_warehouses_list(self):
        """Получает список всех складов из Redis."""
        await self.ensure_connection()
        try:
            keys = await self.redis.keys("warehouse:*")
            warehouses = []
            for key in keys:
                warehouse_data = await self.redis.hgetall(key)
                if warehouse_data:
                    warehouses.append({"id": warehouse_data['id'], "name": warehouse_data['name']})
            return warehouses
        except Exception as e:
            logger.exception(f"Ошибка при получении списка складов: {e}")
            return []

    async def get_warehouse_by_id(self, warehouse_id):
        """Получает информацию о складе по его идентификатору из Redis."""
        await self.ensure_connection()
        try:
            warehouse_key = f"warehouse:{warehouse_id}"
            warehouse_data = await self.redis.hgetall(warehouse_key)

            if not warehouse_data:
                logger.warning(f"Склад с ID {warehouse_id} не найден в Redis.")
                return None

            return warehouse_data
        except Exception as e:
            logger.exception(f"Ошибка при получении данных склада с ID {warehouse_id} из Redis: {e}")
            return None

    async def get_request_status(self, user_id, request_id=None):
        """Проверяет, активен ли запрос пользователя на основе его user_id и request_id."""
        await self.ensure_connection()
        try:
            key = f"user_request:{user_id}:{request_id}" if request_id else f"user_request:{user_id}"
            status_request = await self.redis.hget(key, "status_request")
            return status_request and status_request.lower() == 'true'
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса запроса пользователя {user_id}: {e}")
            return False

    async def stop_request(self, user_id: int, request_id: str):
        """Изменяет статус запроса пользователя на 'False'."""
        await self.ensure_connection()
        try:
            request_key = f"user_request:{user_id}:{request_id}"

            key_exists = await self.redis.exists(request_key)
            if not key_exists:
                logger.error(f"Запрос не найден для пользователя: {user_id} с request_id: {request_id}")
                return False

            result = await self.redis.hset(request_key, 'status_request', 'False')
            if result is not None:
                logger.info(f"Статус запроса {request_id} для пользователя {user_id} успешно обновлен на False.")
                return True
            else:
                logger.error(f"Не удалось обновить статус запроса {request_id} для пользователя {user_id}.")
                return False

        except Exception as e:
            logger.error(f"Ошибка при изменении статуса запроса {request_id} для пользователя {user_id}: {e}")
            return False

    async def add_notify(self, user_id, message):
        """Добавление уведомления в очередь."""
        await self.ensure_connection()
        try:
            await self.redis.rpush('notifications', f'{user_id}:{message}')
            logger.info(f"Уведомление для пользователя {user_id} добавлено в очередь.")
        except Exception as e:
            logger.error(f"Ошибка при добавлении уведомления для пользователя {user_id} в очередь: {e}")

    async def get_all_active_requests(self):
        """Возвращает все активные запросы."""
        keys = await self.redis.keys("user_request:*")
        active_requests = []

        for key in keys:
            if key.count(':') == 2:
                data = await self.redis.hgetall(key)
                if data and data.get('status_request') == 'True':
                    active_requests.append(data)

        return active_requests

    async def is_notification_sent(self, result_id):
        """Проверяет, было ли уже отправлено уведомление с данным идентификатором."""
        await self.ensure_connection()
        try:
            return await self.redis.exists(f"notification_sent:{result_id}") == 1
        except Exception as e:
            logger.error(f"Ошибка при проверке отправленного уведомления {result_id}: {e}")
            return False

    async def mark_notification_as_sent(self, result_id):
        """Отмечает, что уведомление с данным идентификатором было отправлено."""
        await self.ensure_connection()
        try:
            await self.redis.set(f"notification_sent:{result_id}", "True")
            logger.info(f"Уведомление с ID {result_id} отмечено как отправленное.")
        except Exception as e:
            logger.error(f"Ошибка при отметке отправленного уведомления {result_id}: {e}")