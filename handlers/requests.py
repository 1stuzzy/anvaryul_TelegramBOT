from aiogram import types
from loguru import logger

from loader import config
from data import texts
from data.keyboards.main_kbs import requests_keyboard, back_btn
from database.redis_base import RedisClient

redis_client = RedisClient(redis_url=config.redis_url)


async def handle_my_alerts(query: types.CallbackQuery):
    try:
        user_requests = await redis_client.get_user(query.from_user.id)
        if not user_requests:
            await query.answer(texts.requests_not_exists,
                               show_alert=True)
            return

        await query.message.edit_text(texts.active_request_text,
                                      reply_markup=requests_keyboard(user_requests))
    except Exception as e:
        logger.error(f"Error fetching user alerts: {e}")
        await query.message.edit_text(texts.alert_text,
                                      reply_markup=back_btn())


async def handle_request_details(query: types.CallbackQuery):
    try:
        request_index = int(query.data.split('_')[2]) - 1
        if request_index < 0:
            await query.answer(texts.incorrect_request_text)
            return

        user_requests = await redis_client.get_user(query.from_user.id)
        if 0 <= request_index < len(user_requests):
            request = user_requests[request_index]

            await query.message.edit_text(texts.details_text,
                                          reply_markup=back_btn(request.get('date'),
                                                                request.get('status_request')))
        else:
            await query.answer(texts.request_not_exists)
    except Exception as e:
        logger.error(f"Error getting request details: {e}")
        await query.answer(texts.unknown_error_text)


def register_request_handlers(dp):
    dp.callback_query_handler(lambda call: call.data.startswith("request_details_"))(handle_request_details)
    dp.callback_query_handler(lambda call: call.data == "my_requests")(handle_my_alerts)
