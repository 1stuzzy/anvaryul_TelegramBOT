from aiogram import types
from aiogram.dispatcher import FSMContext
from random import randint
from loguru import logger
from loader import bot, config
from database import postgre_base
from data import keyboards, texts, states


async def process_subscribe(query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на подписку."""
    await state.finish()
    if query.data == 'subscribe':
        await query.message.edit_text(
            texts.subscribe_text,
            reply_markup=keyboards.subscribe_kb()
        )
    else:
        await query.answer(
            texts.exception_sub_text,
            show_alert=True
        )
        await query.message.edit_text(
            texts.subscribe_text,
            reply_markup=keyboards.subscribe_kb()
        )


async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс выбора подписки."""
    await state.finish()
    logger.info("Начат процесс выбора подписки")
    await query.message.edit_text(
        texts.select_subtime_text,
        reply_markup=keyboards.subscription_keyboard()
    )


async def handle_subscription_duration(query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор длительности подписки и запрос на оплату."""
    await state.finish()
    logger.info("Обработка выбора длительности подписки")

    duration = query.data.split('_')[1]
    order_id = randint(100000, 999999)

    amount, sub_time = {
        "30": (237.0, "1 месяц"),
        "60": (237.0 * 2, "2 месяца"),
        "90": (237.0 * 3, "3 месяца"),
        "365": (237.0 * 12, "1 год"),
    }.get(duration, (None, None))

    if amount is None:
        return

    await postgre_base.create_payment(user_id=query.from_user.id, summ=amount)

    await state.update_data(order_id=order_id, sub_days=duration, amount=amount)

    await query.message.edit_text(
        texts.ready_pay_text.format(sub_time=sub_time, pay_sum=int(amount), requisites=config.requisites),
        reply_markup=keyboards.payment_btn(order_id, duration),
        disable_web_page_preview=True
    )


async def check_payment_status(query: types.CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя квитанцию для подтверждения платежа."""
    await query.message.edit_text(
        texts.send_reception,
    )
    await states.PaymentVerification.receipt.set()


async def handle_receipt_submission(message: types.Message, state: FSMContext):
    """Обрабатывает квитанцию и отправляет ее администратору."""

    if message.content_type not in ['photo', 'document']:
        await message.answer(texts.send_reception)
        return

    data = await state.get_data()

    order_id = data.get('order_id')
    sub_days = data.get('sub_days')
    amount = data.get('amount')

    if not order_id or not sub_days or amount is None:
        return
    try:
        if message.content_type == 'photo':
            await bot.send_photo(
                config.admins_chat,
                photo=message.photo[-1].file_id,
                caption=texts.new_reception.format(
                    name=message.from_user.full_name,
                    username=message.from_user.username or None,
                    order_id=order_id,
                    sub_days=sub_days,
                    amount=int(amount)
                ),
                reply_markup=keyboards.payment_verification_btn(sub_days, message.from_user.id)
            )
        elif message.content_type == 'document':
            await bot.send_document(
                config.admins_chat,
                document=message.document.file_id,
                caption=texts.new_reception.format(
                    name=message.from_user.full_name,
                    username=message.from_user.username or None,
                    order_id=order_id,
                    sub_days=sub_days,
                    amount=int(amount)
                ),
                reply_markup=keyboards.payment_verification_btn(sub_days, message.from_user.id)
            )
        logger.info("Сообщение успешно отправлено администраторам.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения администраторам: {e}")

    await message.answer(texts.send_reception_true)
    await state.finish()


async def verify_payment_callback(query: types.CallbackQuery):
    """Обрабатывает решение администратора о подтверждении или отклонении платежа."""
    logger.info("Обработка решения администратора")
    data = query.data.split('_')
    action = data[1]
    user_id = int(data[3])
    sub_days = int(data[2])

    try:
        updated_text = ''
        if query.message.text:
            original_text = query.message.text
            if action == "confirm":
                subscription = await postgre_base.grant_subscription(user_id, sub_days)
                end_date = subscription.end_date.strftime('%d.%m.%Y %H:%M')

                await bot.send_message(
                    user_id,
                    texts.sub_success_payed.format(sub_days=sub_days, end_date=end_date)
                )
                updated_text = original_text + "\n\n✅ Платеж подтвержден"
            elif action == "reject":
                await bot.send_message(user_id, texts.requirement_decline)
                updated_text = original_text + "\n\n❌ Платеж отклонен"

            await query.message.edit_text(updated_text, reply_markup=None)
        else:
            if action == "confirm":
                subscription = await postgre_base.grant_subscription(user_id, sub_days)
                end_date = subscription.end_date.strftime('%d.%m.%Y %H:%M')

                await bot.send_message(
                    user_id,
                    texts.sub_success_payed.format(sub_days=sub_days, end_date=end_date)
                )
                await bot.send_message(query.message.chat.id, "✅ Платеж подтвержден.")
            elif action == "reject":
                await bot.send_message(user_id, texts.requirement_decline)
                await bot.send_message(query.message.chat.id, "❌ Платеж отклонен.")

            await query.message.edit_reply_markup(reply_markup=None)

    except Exception as e:
        logger.error(f"Ошибка при обработке платежа: {e}")
        await bot.send_message(query.message.chat.id, "❗ Произошла ошибка при обработке платежа.")


def register_sub2_handlers(dp):
    dp.register_callback_query_handler(process_subscribe, lambda call: call.data in ['subscribe', 'not_subscribe'])
    dp.register_callback_query_handler(process_subscription, lambda call: call.data == 'go_to_subscribe')
    dp.register_callback_query_handler(handle_subscription_duration, lambda call: call.data.startswith("subscribe_"))
    dp.register_callback_query_handler(check_payment_status, lambda call: call.data.startswith("checkpay_"))
    dp.register_message_handler(handle_receipt_submission,
                                state=states.PaymentVerification.receipt,
                                content_types=['photo', 'document'])
    dp.register_callback_query_handler(verify_payment_callback, lambda call: call.data.startswith("payment_"))
