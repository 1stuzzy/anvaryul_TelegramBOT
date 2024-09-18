import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from loguru import logger

from loader import config, dp
from database import postgre_base, models
from data import texts, keyboards, states


async def process_subscribe(query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на подписку."""
    await state.finish()
    if query.data == 'subscribe':
        await query.message.edit_text(texts.subscribe_text,
                                      reply_markup=keyboards.subscribe_kb())
    else:
        await query.answer(texts.exception_sub_text,
                           show_alert=True)
        await query.message.edit_text(texts.subscribe_text,
                                      reply_markup=keyboards.subscribe_kb())


async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс выбора подписки."""
    await state.finish()
    await query.message.edit_text(texts.select_subtime_text,
                                  reply_markup=keyboards.subscription_keyboard())


async def handle_subscription_duration(query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор длительности подписки и запрос на оплату."""
    await state.finish()

    duration = query.data.split('_')[1]
    order_id = random.randint(100000, 999999)

    amount, sub_time = {
        "30": (237.0, "1 месяц"),
        "60": (237.0 * 2, "2 месяца"),
        "90": (237.0 * 3, "3 месяца"),
        "365": (237.0 * 12, "1 год"),
    }.get(duration, (None, None))

    if amount is None:
        return

    await postgre_base.create_payment(user_id=query.from_user.id, summ=amount)

    await query.message.edit_text(
        texts.ready_pay_text.format(sub_time=sub_time, pay_sum=int(amount), requisites=config.requisites),
        reply_markup=keyboards.payment_btn(order_id, duration),
        disable_web_page_preview=True
    )


async def check_payment_status(query: types.CallbackQuery):
    """Напоминает пользователю о необходимости предоставить квитанцию."""
    user = models.User.get_or_none(models.User.user_id == query.from_user.id)
    if not user:
        await query.message.answer("Пользователь не найден.")
        return

    await query.message.answer(
        "Для подтверждения оплаты, пожалуйста, отправьте квитанцию в виде скриншота или документа.",
        reply_markup=keyboards.close_btn()
    )


async def handle_receipt_submission(message: types.Message, state: FSMContext):
    """Обрабатывает квитанцию и отправляет ее в чат администраторов."""
    if message.content_type not in ['photo', 'document']:
        await message.answer("Пожалуйста, отправьте квитанцию в виде скриншота или документа.")
        return

    data = await state.get_data()
    order_id = data.get('order_id')
    sub_days = data.get('sub_days')

    caption = texts.new_reception.format(
        name=message.from_user.full_name,
        username=message.from_user.username or "неизвестен",
        order_id=order_id,
        sub_days=sub_days
    )

    if message.content_type == 'photo':
        await dp.bot.send_photo(
            config.admins_chat,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=keyboards.payment_verification_btn(sub_days, message.from_user.id)
        )
    elif message.content_type == 'document':
        await dp.bot.send_document(
            config.admins_chat,
            document=message.document.file_id,
            caption=caption,
            reply_markup=keyboards.payment_verification_btn(sub_days, message.from_user.id)
        )

    await message.answer(
        "Квитанция отправлена на проверку администратору. Ожидайте подтверждения.",
        reply_markup=keyboards.close_btn()
    )
    await state.finish()


async def verify_payment_callback(query: types.CallbackQuery):
    """Обрабатывает решение администратора о подтверждении или отклонении платежа."""
    action, _, sub_days_str, user_id_str = query.data.split('_')
    user_id = int(user_id_str)
    sub_days = int(sub_days_str)

    if action == "confirm":
        subscription = await postgre_base.grant_subscription(user_id, sub_days)
        end_date = subscription.end_date.strftime('%d.%m.%Y %H:%M')

        await dp.bot.send_message(
            user_id,
            texts.sub_success_payed.format(sub_days=sub_days, end_date=end_date)
        )
        await query.message.edit_text(texts.requirement_payed, reply_markup=keyboards.close_btn())
    elif action == "reject":
        await dp.bot.send_message(user_id, texts.requirement_decline)
        await query.message.edit_text(texts.requirement_decline_admin, reply_markup=keyboards.close_btn())

    logger.info(
        f"Администратор {query.from_user.id} {'подтвердил' if action == 'confirm' else 'отклонил'} платеж пользователя {user_id}."
    )


def register_subscription_handlers(dp):
    """Регистрация обработчиков событий для подписки."""
    dp.callback_query_handler(lambda call: call.data in ['subscribe', 'not_subscribe'], state='*')(process_subscribe)
    dp.callback_query_handler(lambda call: call.data == 'go_to_subscribe', state='*')(process_subscription)
    dp.callback_query_handler(lambda call: call.data.startswith("subscribe_"), state='*')(handle_subscription_duration)
    dp.callback_query_handler(lambda call: call.data.startswith("checkpay_"), state='*')(check_payment_status)
    dp.callback_query_handler(lambda call: call.data.startswith("verify_"), state='*')(verify_payment_callback)
