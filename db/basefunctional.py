import aioredis
import json
from loguru import logger

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
            "accepts_qr": json.dumps(warehouse_data.get('acceptsQr', False))  # Используем значение по умолчанию, если ключ отсутствует
        }
        
        # Сохранение данных в Redis с использованием hset
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
        # Используем hset для записи данных в хэш-ключ Redis
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
        # Формируем ключ для хранения данных о складе в Redis
        warehouse_key = f"warehouse:{warehouse_id}"
        
        # Получаем все поля и их значения для данного склада из Redis
        warehouse_data = await redis.hgetall(warehouse_key)
        
        # Проверяем, что данные были получены
        if not warehouse_data:
            logger.warning(f"Склад с ID {warehouse_id} не найден в Redis.")
            return None

        # Если данные в виде байтов, преобразуем их в строки
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
                # Преобразуем данные только если это байтовые строки
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
