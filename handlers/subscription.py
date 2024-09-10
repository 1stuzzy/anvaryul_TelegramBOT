import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from loguru import logger

from loader import config
from database import postgre_base
from functions.freekassa_api import FreeKassaApi
from data.keyboards.main_kbs import subscribe_kb, subscription_keyboard, payment_btn
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
        "1day": (237.0, "1 день"),
        "3days": (237.0 * 3, "3 дня"),
        "week": (237.0 * 7, "1 Неделя"),
        "month": (237.0 * 30, "1 Месяц"),
    }.get(duration, (None, None))

    if amount is None:
        return

    payment_link = client.generate_payment_link(order_id=order_id, summ=amount)

    await postgre_base.create_payment(user_id=query.from_user.id, summ=amount, )

    await query.message.edit_text(
        texts.ready_pay_text.format(sub_time=sub_time,
                                    pay_sum=int(amount)),
        reply_markup=payment_btn(payment_link),
        disable_web_page_preview=True
    )


async def check_payment_status(query: types.CallbackQuery):
    """Проверяет статус платежа."""
    order_id = query.data.split('_')[1]  # Получаем идентификатор платежа из callback_data

    try:
        # Отправляем запрос на проверку статуса платежа
        payment_status = client.get_order(order_id=order_id)

        if payment_status and payment_status.get('status') == 'success':
            await query.message.answer("Платеж успешно завершен! ✅")
            # Вызываем функцию для обновления данных пользователя, если это необходимо
            #await postgre_base.set_sub_status(query.from_user.id)
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