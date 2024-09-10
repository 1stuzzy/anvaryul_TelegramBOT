import aioredis
from datetime import datetime
from utils import datefunc
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

    async def save_request(self, user_id, warehouse_ids, supply_types,
                           boxTypeID, coefficient, period,
                           notify, status_request=True):
        """Сохраняет запрос пользователя в Redis."""
        key = f"user_request:{user_id}:{datefunc.datetime_local_now()}"

        warehouse_names = ",".join([await self.get_warehouse_name(wh_id) for wh_id in warehouse_ids])

        request_data = {
            "user_id": str(user_id),
            "warehouse_ids": ",".join(map(str, warehouse_ids)),
            "warehouse_name": warehouse_names,
            "date": datefunc.datetime_local_now(),
            "supply_types": ",".join(supply_types),
            "boxTypeID": str(boxTypeID),
            "coefficient": coefficient,
            "period": str(period),
            "notify": str(notify),
            "status_request": str(status_request)
        }

        try:
            await self.redis.hmset(key, mapping=request_data)
            logger.info(f"Запрос пользователя {user_id} успешно сохранен в Redis с ключом {key}.")
        except Exception as e:
            logger.exception(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")

    async def get_warehouse_name(self, warehouse_id):
        """Получает имя склада по его идентификатору."""
        warehouse = await self.get_warehouse_by_id(warehouse_id)
        return warehouse.get('name', 'Неизвестный склад') if warehouse else 'Неизвестный склад'

    async def get_requests_list(self):
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
        """Обновляет коэффициент пользователя."""
        try:
            await self.redis.hset("user:coefficients", user_id, new_coefficient)
            logger.info(f"Коэффициент для пользователя с ID {user_id} обновлен на {new_coefficient}")
        except Exception as e:
            logger.exception(f"Не удалось обновить коэффициент для пользователя с ID {user_id}: {str(e)}")

    async def get_warehouses_list(self):
        """Получает список всех складов из Redis."""
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

    async def get_user(self, user_id):
        """Получает все запросы пользователя из Redis по user_id."""
        try:
            keys_pattern = f"user_request:{user_id}:*"
            keys = await self.redis.keys(keys_pattern)

            user_requests = []
            for key in keys:
                request_data = await self.redis.hgetall(key)
                if request_data:
                    user_requests.append(request_data)

            return user_requests
        except Exception as e:
            logger.exception(f"Ошибка при извлечении запросов пользователя {user_id}: {e}")
            return []

    async def get_request_status(self, user_id):
        """Проверяет, активен ли запрос пользователя на основе его user_id."""
        try:
            keys_pattern = f"user_request:{user_id}:*"
            keys = await self.redis.keys(keys_pattern)
            if not keys:
                logger.warning(f"Запрос для пользователя {user_id} не найден в Redis.")
                return False

            for key in keys:
                status_request = await self.redis.hget(key, "status_request")
                if status_request and status_request.lower() == 'true':
                    return True

            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса запроса пользователя {user_id}: {e}")
            return False

    async def stop_request(self, user_id: int, timestamp: str):
        """Изменяет статус запроса пользователя на 'False'."""
        try:
            request_key = f"user_request:{user_id}:{timestamp}"

            key_exists = await self.redis.exists(request_key)
            if not key_exists:
                logger.error(f"Запрос не найден для пользователя: {user_id} с временной меткой: {timestamp}")
                return False

            result = await self.redis.hset(request_key, 'status_request', 'False')
            if result is None:
                logger.error(f"Не удалось обновить статус запроса для пользователя: {user_id} с временной меткой: {timestamp}")
                return False

            logger.info(f"Статус запроса успешно изменен на False для пользователя: {user_id} с временной меткой: {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при изменении статуса запроса для пользователя {user_id} с временной меткой {timestamp}: {e}")
            return False

    async def delete_request(self, user_id, timestamp):
        """Удаляет запрос пользователя из Redis по user_id и временной метке."""
        try:
            request_key = f"user_request:{user_id}:{timestamp}"
            result = await self.redis.delete(request_key)

            if result == 1:
                logger.info(f"Запрос успешно удален для пользователя: {user_id} с временной меткой: {timestamp}")
                return True
            else:
                logger.error(f"Запрос не найден для пользователя: {user_id} с временной меткой: {timestamp}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при удалении запроса для пользователя {user_id} с временной меткой {timestamp}: {e}")
            return False

    async def add_notify(self, user_id, message):
        """Добавление уведомления в очередь."""
        try:
            await self.redis.rpush('notifications', f'{user_id}:{message}')
            logger.info(f"Уведомление для пользователя {user_id} добавлено в очередь.")
        except Exception as e:
            logger.error(f"Ошибка при добавлении уведомления для пользователя {user_id} в очередь: {e}")
