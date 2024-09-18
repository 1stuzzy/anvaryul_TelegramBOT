import aioredis
import uuid

from loguru import logger
from loader import config


class RedisClient:
    def __init__(self, redis_url):
        self.redis_url = redis_url
        self.redis = None

    async def ensure_connection(self):
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                logger.info("Соединение с Redis установлено.")
            except Exception as e:
                raise e

    async def init(self):
        """Инициализация подключения к Redis."""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def save_request(self, user_id, warehouse_ids, boxTypeID, coefficient, start_date, end_date,
                           status_request=True, notify_until_first=False):
        await self.ensure_connection()
        unique_id = str(uuid.uuid4())
        key = f"user_request:{user_id}:{unique_id}"

        try:
            coefficient = int(coefficient) if coefficient else 0
        except ValueError as e:
            coefficient = 0

        request_data = {
            "request_id": unique_id,
            "user_id": str(user_id),
            "status_request": str(status_request),
            "warehouse_ids": ",".join(map(str, warehouse_ids)),
            "boxTypeID": boxTypeID,
            "coefficient": str(coefficient),  # Сохраняем как строку
            "start_date": start_date,
            "end_date": end_date,
            "notify_until_first": str(notify_until_first)
        }

        try:
            async with self.redis.pipeline() as pipe:
                await pipe.hmset(key, mapping=request_data)
                await pipe.execute()
            await self.redis.bgsave()
        except Exception as e:
            logger.exception(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")

    async def get_user_requests(self, user_id):
        await self.ensure_connection()
        if self.redis is None:
            logger.error("Соединение с Redis не установлено.")
            return []

        try:
            keys_pattern = f"user_request:{user_id}:*"
            keys = await self.redis.keys(keys_pattern)

            if not keys:
                return []

            async with self.redis.pipeline() as pipe:
                for key in keys:
                    pipe.hgetall(key)
                user_requests = await pipe.execute()

            return [req for req in user_requests if req.get("user_id") == str(user_id)]
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
            if not keys:
                return []

            async with self.redis.pipeline() as pipe:
                for key in keys:
                    pipe.hgetall(key)
                user_requests = await pipe.execute()

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
            if not keys:
                return []

            async with self.redis.pipeline() as pipe:
                for key in keys:
                    pipe.hgetall(key)
                warehouses = await pipe.execute()

            return [{"id": wh['id'], "name": wh['name']} for wh in warehouses if wh]
        except Exception as e:
            logger.exception(f"Ошибка при получении списка складов: {e}")
            return []

    async def get_warehouse_by_id(self, warehouse_id):
        """Получает информацию о складе по его идентификатору из Redis."""
        await self.ensure_connection()
        try:
            warehouse_key = f"warehouse:{warehouse_id}"
            return await self.redis.hgetall(warehouse_key)
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

            if not await self.redis.exists(request_key):
                logger.error(f"Запрос не найден для пользователя: {user_id} с request_id: {request_id}")
                return False

            result = await self.redis.hset(request_key, 'status_request', 'False')
            if result is not None and result > 0:
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
        await self.ensure_connection()
        try:
            keys = await self.redis.keys("user_request:*")
            if not keys:
                return []

            async with self.redis.pipeline() as pipe:
                for key in keys:
                    pipe.hgetall(key)
                active_requests = await pipe.execute()

            return [req for req in active_requests if req.get('status_request') == 'True']
        except Exception as e:
            logger.error(f"Ошибка при получении активных запросов: {e}")
            return []

    async def is_notification_sent(self, message_id):
        """Проверяет, было ли уведомление с данным идентификатором отправлено недавно."""
        try:
            return await self.redis.exists(f"notification_sent:{message_id}")
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса уведомления в Redis: {e}")
            return False

    async def mark_notification_as_sent(self, message_id, delay):
        """Помечает уведомление как отправленное с указанным временем жизни."""
        try:
            await self.redis.set(f"notification_sent:{message_id}", 1, ex=delay)
        except Exception as e:
            logger.error(f"Ошибка при сохранении статуса уведомления в Redis: {e}")