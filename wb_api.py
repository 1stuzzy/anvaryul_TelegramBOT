import aiohttp
import ssl
import asyncio
from aiogram import Bot
from loader import config
from loguru import logger
from db.basefunctional import init_redis, save_warehouse, get_user_requests, add_notification_to_queue, update_user_coefficient, get_user_by_alert_id

async def fetch_warehouses():
    headers = {"Authorization": f"{config.api_key}"}
    url = 'https://supplies-api.wildberries.ru/api/v1/warehouses'

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, ssl=ssl_context) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Ошибка при получении данных: {response.status} - {await response.text()}")
                return None

async def get_coefficients(warehouse_ids=None, headers=None):
    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
    params = {'warehouseIDs': ','.join(map(str, warehouse_ids))} if warehouse_ids else {}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.error(f"Превышен лимит запросов к API: {await response.text()}")
                    await asyncio.sleep(60)
                    return None
                else:
                    logger.error(f"Ошибка при запросе к API: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            logger.exception(f"Произошла ошибка при запросе к API: {e}")
            return None

async def check_and_notify_users(bot: Bot):
    redis = await init_redis()
    headers = {"Authorization": f"{config.api_key}"}

    while True:
        try:
            user_requests = await get_user_requests(redis)
            
            for request in user_requests:
                coefficients = await get_coefficients(
                    warehouse_ids=request['warehouse_ids'].split(','),
                    headers=headers
                )
                
                if coefficients:
                    relevant_changes = [
                        coef for coef in coefficients
                        if coef['coefficient'] <= int(request['coefficient']) and
                        str(coef['warehouseID']) in request['warehouse_ids'] and
                        coef['boxTypeName'] in request['supply_types']
                    ]
                    
                    if relevant_changes:
                        messages = [
                            f"📦 <b>Обновление по складу {change['warehouseName']}</b>\n"
                            f"Тип поставки: {change['boxTypeName']}\n"
                            f"Дата: {change['date']}\n"
                            f"Коэффициент приёмки: {change['coefficient']}\n"
                            for change in relevant_changes
                        ]
                        final_message = "\n".join(messages)
                        await add_notification_to_queue(redis, request['user_id'], final_message)
                        await bot.send_message(request['user_id'], final_message)

            await asyncio.sleep(60)
        
        except Exception as e:
            logger.error(f"Ошибка при проверке и уведомлении: {e}")
            await asyncio.sleep(60)

async def fetch_coefficient(session, user_id, alert_params):
    """Функция для выполнения запроса к API WB и получения коэффициента."""
    url = 'https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients'
    try:
        async with session.get(url, params=alert_params) as response:
            response_data = await response.json()
            return response_data.get("coefficient")
    except Exception as e:
        logger.error(f"Ошибка при запросе коэффициента для пользователя {user_id}: {e}")
        return None

async def notify_user(bot: Bot, user_id: int, new_coefficient: float):
    """Уведомляет пользователя об изменении коэффициента."""
    try:
        await bot.send_message(
            user_id,
            f"Уведомление: коэффициент по вашему запросу изменился на {new_coefficient:.2f}"
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")

async def process_notifications(bot: Bot, alert_id: int, alert_params: dict, interval: int = 60):
    """
    Задача, которая периодически проверяет коэффициент по запросу и уведомляет пользователя, если он изменился.
    
    :param bot: Экземпляр бота для отправки уведомлений.
    :param alert_id: Идентификатор запроса пользователя.
    :param alert_params: Параметры для запроса к API WB.
    :param interval: Интервал проверки в секундах.
    """
    async with aiohttp.ClientSession() as session:
        user = await get_user_by_alert_id(alert_id)
        if not user:
            logger.error(f"Пользователь для запроса с ID {alert_id} не найден")
            return
        
        previous_coefficient = user.get("coefficient", None)

        while True:
            new_coefficient = await fetch_coefficient(session, user['id'], alert_params)
            
            if new_coefficient is not None and new_coefficient != previous_coefficient:
                await update_user_coefficient(user['id'], new_coefficient)
                await notify_user(bot, user['id'], new_coefficient)
                previous_coefficient = new_coefficient
            
            await asyncio.sleep(interval)
