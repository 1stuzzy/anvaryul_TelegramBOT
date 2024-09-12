from aiogram import types
from aiogram.dispatcher import FSMContext
from loguru import logger

from database import postgre_base
from data import texts
from data.keyboards.keyboard import warehouse_markup
from handlers.subscription import process_subscribe


async def process_create_alert(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    await state.reset_state(with_data=True)
    await state.update_data(selected_warehouses=[])

    is_subscribed = await postgre_base.check_subscription(query.from_user.id)

    try:
        if is_subscribed:
            markup = await warehouse_markup(redis_client, [])
            await query.message.edit_text(texts.select_warehouse_text.format(), reply_markup=markup)
        else:
            await process_subscribe(query, state)
    except Exception as e:
        logger.error(f"Error processing create alert: {e}")


def register_alert_handlers(dp):
    dp.callback_query_handler(lambda call: call.data == 'create_alert', state='*')(process_create_alert)
