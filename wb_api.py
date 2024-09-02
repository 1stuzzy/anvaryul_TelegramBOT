import aioredis
import aiohttp
import asyncio
from loader import config, dp
from loguru import logger
from aiogram.utils.exceptions import Throttled
from db.models import UserRequest

headers = {"Authorization": f"{config.api_key}"}


async def get_coefficients(warehouse_id=None):
    params = {}
    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    if warehouse_id:
        if isinstance(warehouse_id, list):
            params['warehouseIDs'] = ','.join(map(str, warehouse_id))
        else:
            params['warehouseIDs'] = str(warehouse_id)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.error(f"Превышен лимит запросов к API: {await response.text()}")
                    await asyncio.sleep(60)  # Задержка перед повторной попыткой
                    return None
                else:
                    logger.error(f"Ошибка при запросе к API: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            logger.exception(f"Произошла ошибка при запросе к API: {e}")
            return None


async def check_and_notify_users(redis):
    while True:
        try:
            user_requests = UserRequest.select()
            for request in user_requests:
                coefficients = await get_coefficients(request.warehouse_ids.split(','))
                if not coefficients:
                    logger.warning(f"Не удалось получить данные для складов: {request.warehouse_ids}")
                    continue

                relevant_changes = []
                for coef in coefficients:
                    if (str(coef['warehouseID']) in request.warehouse_ids.split(',') and
                            coef['boxTypeName'] in request.supply_types.split(',') and
                            coef['coefficient'] <= int(request.coefficient)):
                        relevant_changes.append(coef)

                if relevant_changes:
                    messages = []
                    for change in relevant_changes:
                        message = (
                            f"📦 <b>Обновление по складу {change['warehouseName']}</b>\n"
                            f"Тип поставки: {change['boxTypeName']}\n"
                            f"Дата: {change['date']}\n"
                            f"Коэффициент приёмки: {change['coefficient']}\n"
                        )
                        messages.append(message)

                    final_message = "\n".join(messages)
                    await add_notification_to_queue(redis, request.user_id, final_message)

            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка при проверке обновлений и уведомлений: {e}")


async def init_redis():
    return await aioredis.from_url('redis://localhost', decode_responses=True)


async def process_notifications(redis):
    try:
        while True:
            notification_data = await redis.blpop('notifications', timeout=0)
            if notification_data:
                user_id, message = notification_data[1].split(':', 1)
                await send_notification(user_id, message)
    except asyncio.CancelledError:
        logger.info("Задача process_notifications была отменена.")
    finally:
        await redis.close()


async def send_notification(user_id, message):
    try:
        await dp.bot.send_message(user_id, message)
    except Throttled:
        await asyncio.sleep(1)
        await dp.bot.send_message(user_id, message)


async def add_notification_to_queue(redis, user_id, message):
    await redis.rpush('notifications', f'{user_id}:{message}')
