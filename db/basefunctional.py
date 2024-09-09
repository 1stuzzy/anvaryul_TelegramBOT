import aioredis
import json
from loguru import logger
from db.models import User, Payment
from typing import Optional
from datetime import date



async def init_redis():
    """Инициализация подключения к Redis."""
    return await aioredis.from_url('redis://localhost', decode_responses=True)


async def save_warehouse(redis, warehouse_data):
    """Сохранение склада в Redis."""
    try:
        warehouse_key = f"warehouse:{warehouse_data['ID']}"
        warehouse_dict = {
            "id": warehouse_data['ID'],
            "name": warehouse_data['name'],
            "address": warehouse_data['address'],
            "work_time": warehouse_data['workTime'],
        }
        
        await redis.hset(warehouse_key, mapping=warehouse_dict)
        logger.info(f"Склад с ID {warehouse_data['ID']} успешно сохранен в Redis.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении склада в Redis: {e}")


async def save_user_request_to_redis(redis, user_id, warehouse_ids, supply_types, coefficient, period, notification_type):
    """
    Сохраняет запрос пользователя в Redis.

    :param redis: Экземпляр Redis.
    :param user_id: Идентификатор пользователя.
    :param warehouse_ids: Идентификаторы складов.
    :param supply_types: Типы поставок.
    :param coefficient: Коэффициент приемки.
    :param period: Период поиска.
    :param notification_type: Тип уведомления (0 - до первого уведомления, 1 - без ограничений).
    """
    key = f"user_request:{user_id}"
    request_data = {
        "warehouse_ids": warehouse_ids,
        "supply_types": supply_types,
        "coefficient": coefficient,
        "period": period,
        "notification_type": notification_type,
    }
    try:
        for field, value in request_data.items():
            await redis.hset(key, field, value)
        
        logger.info(f"Запрос пользователя {user_id} успешно сохранен в Redis.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя {user_id} в Redis: {e}")


async def get_warehouse_by_id(redis, warehouse_id):
    """
    Получает информацию о складе по его идентификатору из Redis.

    :param redis: Экземпляр Redis.
    :param warehouse_id: Идентификатор склада.
    :return: Словарь с информацией о складе, включая его имя.
    """
    try:
        warehouse_key = f"warehouse:{warehouse_id}"
        
        warehouse_data = await redis.hgetall(warehouse_key)
        
        if not warehouse_data:
            logger.warning(f"Склад с ID {warehouse_id} не найден в Redis.")
            return None

        warehouse_data = {
            k.decode('utf-8') if isinstance(k, bytes) else k: 
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in warehouse_data.items()
        }

        return warehouse_data

    except Exception as e:
        logger.error(f"Ошибка при получении данных склада с ID {warehouse_id} из Redis: {e}")
        return None


async def get_warehouses(redis):
    try:
        warehouses_keys = await redis.keys("warehouse:*")
        warehouses = []
        for key in warehouses_keys:
            warehouse_data = await redis.hgetall(key)
            warehouses.append({"id": warehouse_data['id'], "name": warehouse_data['name']})
        return warehouses
    except Exception as e:
        logger.error(f"Ошибка при получении списка складов: {e}")
        return []


async def get_user_requests(redis):
    """
    Получает все активные запросы пользователей из Redis.
    :param redis: Экземпляр Redis.
    :return: Список запросов пользователей.
    """
    try:
        # Получаем все ключи, связанные с запросами пользователей
        keys = await redis.keys('user_request:*')
        
        user_requests = []
        for key in keys:
            request_data = await redis.hgetall(key)
            if request_data:
                request_data = {
                    k.decode('utf-8') if isinstance(k, bytes) else k: 
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in request_data.items()
                }
                user_requests.append(request_data)

        return user_requests

    except Exception as e:
        logger.error(f"Ошибка при получении запросов пользователей: {e}")
        return []


async def add_notification_to_queue(redis, user_id, message):
    """Добавление уведомления в очередь."""
    await redis.rpush('notifications', f'{user_id}:{message}')


async def get_user_request_status(self, user_id: int) -> bool:
    """
    Проверяет, активен ли запрос пользователя на основе его user_id.

    :param user_id: Идентификатор пользователя
    :return: True, если запрос активен, иначе False
    """
    try:
        user_request_key = f"user_request:{user_id}"

        user_request = await self.redis.hgetall(user_request_key)

        if not user_request:
            logger.warning(f"Запрос для пользователя {user_id} не найден в Redis.")
            return False

        status_request = user_request.get('status_request', 'false').lower() == 'true'
        return status_request

    except Exception as e:
        logger.error(f"Ошибка при получении статуса запроса пользователя {user_id}: {e}")
        return False


"""
PostgreSQL Base
"""


async def create_user(user_id: int, name: str, username: str, subscription: bool = False, sub_date: Optional[date] = None):
    user = User.create(
        user_id=user_id,
        name=name,
        username=username,
        subscription=subscription,
        sub_date=sub_date)
    return user



async def check_subscription(user_id: int) -> bool:
    user = User.get(User.user_id == user_id)  # Используем синхронный метод, если асинхронный не работает
    if user:
        print(f"User found: {user.username}, Subscription: {user.subscription}")  # Отладочное сообщение
        return user.subscription
    print("User not found or no subscription.")  # Отладочное сообщение, если пользователь не найден
    return False

