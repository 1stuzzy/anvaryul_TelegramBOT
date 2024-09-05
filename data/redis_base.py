import aioredis
import json
from datetime import datetime
from loguru import logger


class RedisClient:
    def __init__(self, redis_url='redis://localhost'):
        self.redis_url = redis_url
        self.redis = None

    async def init(self):
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def save_user_request(self, user_id, warehouse_ids, supply_types, boxTypeID, coefficient, period, notify):
        timestamp = datetime.utcnow().strftime('%d.%m.%Y.%H:%M')
        key = f"user_request:{user_id}:{timestamp}"

        warehouse_names = ",".join([await self.get_warehouse_name(wh_id) for wh_id in warehouse_ids])

        request_data = {
            "user_id": str(user_id),
            "warehouse_ids": ",".join(map(str, warehouse_ids)),
            "warehouse_name": warehouse_names,
            "date": timestamp,
            "supply_types": ",".join(supply_types),
            "boxTypeID": str(boxTypeID),
            "coefficient": coefficient,
            "period": str(period),
            "notify": str(notify),
        }

        try:
            await self.redis.hmset(key, mapping=request_data)
            logger.info(f"Запрос пользователя {user_id} успешно сохранен в Redis с ключом {key}.")
        except Exception as e:
            logger.exception(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")

    async def get_warehouse_name(self, warehouse_id):
        """Получает имя склада по его идентификатору."""
        warehouse = await self.get_warehouse_by_id(warehouse_id)
        return warehouse.get('name', 'Неизвестный склад')

    async def get_user_requests(self):
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

    async def update_user_coefficient(self, user_id, new_coefficient):
        try:
            await self.redis.hset("user:coefficients", user_id, new_coefficient)
            logger.info(f"Коэффициент для пользователя с ID {user_id} обновлен на {new_coefficient}")
        except Exception as e:
            logger.exception(f"Не удалось обновить коэффициент для пользователя с ID {user_id}: {str(e)}")

    async def get_warehouses(self):
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

    @staticmethod
    async def upload_warehouses(wb_api, redis_client):
        """Загружает и сохраняет информацию о складских центрах в Redis."""
        try:
            distribution_centers = await wb_api.parse_warehouses()  # Вызываем метод parse_warehouses
            if distribution_centers:
                await redis_client.save_distribution_centers(distribution_centers)
                logger.info("Складские центры успешно загружены и сохранены в Redis.")
            else:
                logger.warning("Складские центры не были загружены: пустой ответ от API.")
        except Exception as e:
            logger.exception(f"Ошибка при загрузке складских центров: {e}")

    async def save_distribution_centers(self, distribution_centers):
        try:
            for center in distribution_centers:
                key = f"warehouse:{center['id']}"
                await self.redis.hmset(key, mapping=center)
            logger.info("Складские центры успешно сохранены в Redis.")
        except Exception as e:
            logger.exception(f"Ошибка при сохранении складских центров в Redis: {e}")

    async def get_user(self, user_id):
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

    async def delete_user_request(self, user_id: int, timestamp: str):
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
