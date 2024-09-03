import aioredis
from loguru import logger


class RedisClient:
    def __init__(self, redis_url='redis://localhost'):
        self.redis_url = redis_url
        self.redis = None

    async def init(self):
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def save_user_request(self, user_id, warehouse_ids, supply_types, boxTypeID, coefficient, period, status):
        key = f"user_request:{user_id}"

        warehouse_ids_str = ",".join(map(str, warehouse_ids))
        supply_types_str = ",".join(supply_types)

        request_data = {
            "user_id": str(user_id),
            "warehouse_ids": warehouse_ids_str,
            "supply_types": supply_types_str,
            "boxTypeID": str(boxTypeID),
            "coefficient": str(coefficient),
            "period": str(period),
            "status": str(status),
        }

        try:
            existing_request = await self.redis.hgetall(key)

            if existing_request:
                existing_request_str = {k.decode('utf-8'): v.decode('utf-8') for k, v in existing_request.items()}
                if existing_request_str == request_data:
                    logger.info(f"Запрос пользователя {user_id} уже существует, повторное сохранение не требуется.")
                    return

            await self.redis.hmset(key, mapping=request_data)
            logger.info(f"Запрос пользователя {user_id} успешно сохранен в Redis.")
        except Exception as e:
            logger.exception(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")



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
