from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from html import escape
from loguru import logger
from loader import dp, config
from database.models import User
from database import postgre_base, redis_base
from data.keyboards import keyboard
from data import texts
from functions.freekassa_api import FreeKassaApi
import random
from aiogram.utils.exceptions import MessageNotModified

async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text("Выберите срок подписки:", reply_markup=keyboard.subscription_keyboard())

async def handle_subscription_duration(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    duration = query.data.split('_')[1]
    order_id = random.randint(100000, 999999)

    if duration == "1day":
        amount = 237.0
        description = "Подписка на 1 день"
    elif duration == "3days":
        amount = 237.0 * 3
        description = "Подписка на 3 дня"
    elif duration == "week":
        amount = 237.0 * 7
        description = "Подписка на неделю"
    elif duration == "month":
        amount = 237.0 * 30
        description = "Подписка на месяц"
    else:
        await query.message.edit_text("Неверный срок подписки.")
        return

    payment_link = FreeKassaApi.generate_payment_link(order_id=order_id, summ=amount)
    await query.message.edit_text(
        f"Для оплаты подписки на выбранный срок перейдите по ссылке: [Оплатить]({payment_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def process_create_alert(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    await state.reset_state(with_data=True)
    await state.update_data(selected_warehouses=[])

    is_subscribed = await postgre_base.check_subscription(query.from_user.id)

    try:
        if is_subscribed:
            markup = await keyboard.warehouse_markup(redis_client, [])
            await query.message.edit_text(texts.select_warehouse_text, reply_markup=markup)
        else:
            await process_subscription(query, state)
    except MessageNotModified:
        pass

    if query.data == 'premium_alert':
        await query.answer('🛠 В разработке...')

async def process_go_back(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer_sticker(texts.hi_sticker, reply_markup=keyboard.main_keyboard())
    await query.message.answer(texts.menu_text, reply_markup=keyboard.menu_keyboard())
    await query.answer()

async def process_cancel(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer_sticker(texts.hi_sticker, reply_markup=keyboard.main_keyboard())
    await query.message.answer(texts.menu_text, reply_markup=keyboard.menu_keyboard())
    await query.answer()

async def handle_select_callback(call: types.CallbackQuery, state: FSMContext):
    redis_client = call.bot.get('redis_client')
    try:
        data_parts = call.data.split("_")
        if len(data_parts) < 2:
            logger.error(f"Неверный формат данных callback: {call.data}")
            await call.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return

        action = data_parts[0]
        warehouse_id_str = data_parts[1]

        if not warehouse_id_str.isdigit():
            logger.error(f"Неверный warehouse_id: {warehouse_id_str}")
            await call.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return

        warehouse_id = int(warehouse_id_str)
        user_data = await state.get_data()
        selected_warehouses = user_data.get("selected_warehouses", [])

        if action == "select" and warehouse_id not in selected_warehouses:
            selected_warehouses.append(warehouse_id)
        elif action == "unselect" and warehouse_id in selected_warehouses:
            selected_warehouses.remove(warehouse_id)

        await state.update_data(selected_warehouses=selected_warehouses)

        updated_markup = await keyboard.warehouse_markup(
            redis_client=redis_client,
            selected_warehouses=selected_warehouses,
        )
        await keyboard.update_markup(call.message, updated_markup)
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке callback-данных: {e}")
        await call.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")



async def handle_continue_supply(call: types.CallbackQuery):
    try:
        await call.message.edit_text(texts.select_supply_text,
                                     reply_markup=keyboard.supply_types_markup())
    except Exception as e:
        logger.error(f"Ошибка в handle_continue_supply: {e}")
        await call.message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")


async def process_supply_type_selection(callback_query: types.CallbackQuery, state: FSMContext):
    action, supply_type = callback_query.data.split('_', 1)

    user_data = await state.get_data()
    selected_supply_types = user_data.get("selected_supply_types", set())

    if action == "selecttype":
        selected_supply_types.add(supply_type)
    elif action == "unselecttype":
        selected_supply_types.discard(supply_type)

    await state.update_data(selected_supply_types=selected_supply_types)
    await callback_query.message.edit_reply_markup(reply_markup=keyboard.supply_types_markup(selected_supply_types))


async def handle_continue_coeff(call: types.CallbackQuery):
    try:
        await call.message.edit_text(texts.select_coefficient_text, reply_markup=keyboard.acceptance_coefficient_markup())
    except Exception as e:
        logger.error(e)

async def process_coefficient_selection(query: types.CallbackQuery, state: FSMContext):
    coefficient = query.data.split('_')[1]
    await state.update_data(coefficient=coefficient)
    await dp.bot.answer_callback_query(query.id)
    await query.message.edit_text(texts.select_period_text, reply_markup=keyboard.period_selection_markup())

async def process_period_selection(query: types.CallbackQuery, state: FSMContext):
    await dp.bot.answer_callback_query(query.id)

    period = query.data.split('_')[-1]
    selected_period = texts.period_map.get(period, "Неизвестный период")
    await state.update_data(period=selected_period)

    await query.message.edit_text(texts.alert_text, reply_markup=keyboard.notification_count_markup())

async def process_notification_count_selection(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    try:
        user_data = await state.get_data()

        warehouse_ids = user_data.get("selected_warehouses", [])
        supply_types = user_data.get("selected_supply_types", [])
        coefficient = user_data.get("coefficient", "")

        coefficient_range = coefficient if not coefficient.startswith("<") else f"<{float(coefficient[1:])}"

        supply_types_names = ', '.join(texts.types_map.get(st, st) for st in supply_types)
        period = user_data.get("period", "Неизвестный период")

        warehouse_names = []
        for wh_id in warehouse_ids:
            warehouse = await redis_client.get_warehouse_by_id(wh_id)
            if warehouse:
                warehouse_names.append(warehouse.get('name', ''))

        warehouse_names = ', '.join(warehouse_names)

        notification_type = 0 if query.data == "notify_once" else 1

        boxTypeIDs = [texts.supply_map.get(st) for st in supply_types if st in texts.types_map]

        await redis_client.save_user_request(
            user_id=query.from_user.id,
            warehouse_ids=warehouse_ids,
            supply_types=supply_types,
            boxTypeID=','.join(boxTypeIDs),
            coefficient=coefficient_range,
            period=period,
            notify=notification_type,
            status_request=True
        )

        if coefficient_range.startswith('<') and coefficient_range != "0":
            coefficient_sign = "<"
        else:
            coefficient_sign = ""

        final_text = texts.notification_text.format(
            warehouse_names=escape(warehouse_names),
            period=escape(period),
            supply_types_names=escape(supply_types_names),
            coefficient=escape(coefficient_sign + coefficient_range.lstrip('<'))
        )

        await query.message.edit_text(final_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя в Redis: {e}")
        await query.message.answer("Произошла ошибка при сохранении вашего запроса. Пожалуйста, попробуйте позже.")


def register_main_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(handle_continue_supply, lambda call: call.data == 'continue_supply', state='*')
    dp.register_callback_query_handler(handle_continue_coeff, lambda call: call.data == 'continue_suppl_coeff', state='*')
    dp.register_callback_query_handler(process_coefficient_selection, Text(startswith="coefficient_"), state='*')
    dp.register_callback_query_handler(process_period_selection, Text(startswith="period_"), state='*')
    dp.register_callback_query_handler(process_notification_count_selection, lambda call: call.data in ['notify_once', 'notify_unlimited'], state='*')
    dp.register_callback_query_handler(process_subscription, lambda call: call.data == 'go_to_subscribe', state='*')
    dp.register_callback_query_handler(handle_subscription_duration, Text(startswith="subscribe_"), state='*')
    dp.register_callback_query_handler(process_create_alert, lambda call: call.data == 'create_alert', state='*')
    dp.register_callback_query_handler(process_go_back, lambda call: call.data == "back_menu")
    dp.register_callback_query_handler(process_cancel, lambda call: call.data == "cancel")
    dp.register_callback_query_handler(handle_select_callback, lambda call: call.data.startswith(("select_", "unselect_")), state='*')
    dp.register_callback_query_handler(process_supply_type_selection, lambda c: c.data and (c.data.startswith('selecttype_') or c.data.startswith('unselecttype_')), state='*')
