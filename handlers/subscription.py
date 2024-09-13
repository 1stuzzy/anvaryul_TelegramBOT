import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from loguru import logger

from loader import config
from database import postgre_base, models
from functions.freekassa_api import FreeKassaApi
from data.keyboards import subscribe_kb, subscription_keyboard, payment_btn
from data import texts

client = FreeKassaApi(
    merchant_id=config.merchant_id,
    first_secret=config.first_secret,
    second_secret=config.second_secret
)


async def process_subscribe(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if query.data == 'subscribe':
        await query.message.edit_text(texts.subscribe_text,
                                      reply_markup=subscribe_kb())
    else:
        await query.answer(texts.exception_sub_text,
                           show_alert=True)
        await query.message.edit_text(texts.subscribe_text,
                                      reply_markup=subscribe_kb())


async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text(texts.select_subtime_text,
                                  reply_markup=subscription_keyboard())


async def handle_subscription_duration(query: types.CallbackQuery, state: FSMContext):
    await state.finish()

    duration = query.data.split('_')[1]
    order_id = random.randint(100000, 999999)

    amount, sub_time = {
        "1": (237.0, "1 день"),
        "3": (237.0 * 3, "3 дня"),
        "7": (237.0 * 7, "1 Неделя"),
        "30": (237.0 * 30, "1 Месяц"),
    }.get(duration, (None, None))

    if amount is None:
        return

    payment_link = client.generate_payment_link(order_id=order_id, summ=amount)

    await postgre_base.create_payment(user_id=query.from_user.id, summ=amount)

    await query.message.edit_text(
        texts.ready_pay_text.format(sub_time=sub_time, pay_sum=int(amount)),
        reply_markup=payment_btn(payment_link, order_id, duration),  # Pass the duration here
        disable_web_page_preview=True
    )


async def check_payment_status(query: types.CallbackQuery):
    """Проверяет статус платежа."""
    user = models.User.get(models.User.user_id == query.from_user.id)
    try:
        # Extract order_id and sub_days from the callback data
        _, order_id, sub_days_str = query.data.split('_')
        sub_days = int(sub_days_str)  # Convert sub_days to integer

        # Check the payment status
        payment_status = client.get_order(order_id=order_id)

        if payment_status:
            status = payment_status.get('status').lower() if payment_status.get('status') else ''
            if status in ['success', 'paid', 'access', 'ok']:
                await query.message.answer("Платеж успешно завершен! ✅")
                if user.subscription == True:
                    await postgre_base.grant_subscription(query.from_user.id, int(sub_days))
                else:
                    return
                await postgre_base.set_pay_status(query.from_user.id, status)
                await postgre_base.grant_subscription(query.from_user.id, sub_days)
            else:
                await query.message.answer("Платеж не найден или еще не завершен. Попробуйте позже. ❌")
        else:
            await query.message.answer("Платеж не найден или еще не завершен. Попробуйте позже. ❌")

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса платежа: {e}")
        await query.message.answer("Произошла ошибка при проверке платежа. Пожалуйста, попробуйте позже.")


def register_subscription_handlers(dp):
    dp.callback_query_handler(lambda call: call.data in ['subscribe', 'not_subscribe'], state='*')(process_subscribe)
    dp.callback_query_handler(lambda call: call.data == 'go_to_subscribe', state='*')(process_subscription)
    dp.callback_query_handler(lambda call: call.data.startswith("subscribe_"), state='*')(handle_subscription_duration)
    dp.callback_query_handler(lambda call: call.data.startswith("checkpay_"), state='*')(check_payment_status)