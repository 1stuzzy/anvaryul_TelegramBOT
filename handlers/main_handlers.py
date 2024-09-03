from loader import dp
from aiogram import types
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from loguru import logger
from data.texts import *
from data.keyboards.main_kbs import (main_keyboard, menu_keyboard, alerts_keyboard, type_alert,
                                     warehouse_markup, update_markup, supply_types_markup,
                                     acceptance_coefficient_markup, notification_count_markup,
                                     start_bot_markup, period_selection_markup)


@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(START_TEXT, reply_markup=main_keyboard())
    await message.answer(MAIN_MENU_TEXT, reply_markup=menu_keyboard())


@dp.message_handler(Text(equals="🔔 Оповещения"), state='*')
@dp.callback_query_handler(lambda call: call.data == 'alerts')
async def process_alerts(query, state=FSMContext):
    await state.finish()
    chat_id, message_id = (query.chat.id,
                           query.message_id) if isinstance(query, types.Message) else (query.message.chat.id,
                                                                                       query.message.message_id)
    await dp.bot.send_message(chat_id, ALERTS_TEXT, reply_markup=alerts_keyboard())


@dp.callback_query_handler(lambda call: call.data == 'create_alert')
async def process_create_alert(query: types.CallbackQuery):
    await dp.bot.answer_callback_query(query.id)
    try:
        await query.message.edit_text(CREATE_ALERT_TEXT, reply_markup=type_alert())
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda call: call.data == 'default_alert', state='*')
async def process_default_alert(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    await state.reset_state(with_data=True)
    await dp.bot.answer_callback_query(query.id)
    await state.update_data(selected_warehouses=[])

    try:
        markup = await warehouse_markup(redis_client, [])
        await query.message.edit_text(SELECT_WAREHOUSE_TEXT, reply_markup=markup)
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda call: call.data.startswith("page_"))
async def handle_page_callback(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    direction, page = query.data.split("_")[1], int(query.data.split("_")[2])
    user_data = await state.get_data()
    selected_warehouses = user_data.get("selected_warehouses", [])

    all_warehouses = await redis_client.get_warehouses()
    total_pages = (len(all_warehouses) + 15) // 16

    if direction == "back" and page > 0:
        page -= 1
    elif direction == "forward" and page < total_pages - 1:
        page += 1
    else:
        await query.answer("Вы уже на первой/последней странице.", show_alert=True)
        return

    await update_markup(query.message, await warehouse_markup(redis_client, selected_warehouses, page))


@dp.callback_query_handler(lambda call: call.data.startswith(("select_", "unselect_")))
async def handle_select_callback(call: types.CallbackQuery, state: FSMContext):
    redis_client = call.bot.get('redis_client')
    try:
        data_parts = call.data.split("_")
        action = data_parts[0]
        warehouse_id_str = data_parts[1]
        page_str = data_parts[3]

        if warehouse_id_str.isdigit() and page_str.isdigit():
            warehouse_id = int(warehouse_id_str)
            page = int(page_str)

            user_data = await state.get_data()
            selected_warehouses = user_data.get("selected_warehouses", [])

            if action == "select" and warehouse_id not in selected_warehouses:
                selected_warehouses.append(warehouse_id)
            elif action == "unselect" and warehouse_id in selected_warehouses:
                selected_warehouses.remove(warehouse_id)

            await state.update_data(selected_warehouses=selected_warehouses)

            updated_markup = await warehouse_markup(redis_client=redis_client,
                                                    selected_warehouses=selected_warehouses,
                                                    page=page)
            await update_markup(call.message, updated_markup)
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке callback-данных: {e}")


@dp.callback_query_handler(lambda call: call.data == "continue")
async def handle_continue_callback(call: types.CallbackQuery):
    await dp.bot.answer_callback_query(call.id)
    await call.message.edit_text(SELECT_SUPPLY_TYPES_TEXT, reply_markup=supply_types_markup())


@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('selecttype_')
                                                 or c.data.startswith('unselecttype_')))
async def process_supply_type_selection(callback_query: types.CallbackQuery, state: FSMContext):
    action, supply_type = callback_query.data.split('_', 1)

    user_data = await state.get_data()
    selected_supply_types = user_data.get("selected_supply_types", set())

    if action == "selecttype":
        selected_supply_types.add(supply_type)
    elif action == "unselecttype":
        selected_supply_types.discard(supply_type)

    await state.update_data(selected_supply_types=selected_supply_types)
    await callback_query.message.edit_reply_markup(reply_markup=supply_types_markup(selected_supply_types))


@dp.callback_query_handler(lambda call: call.data == "continue_supply")
async def handle_continue_callback(call: types.CallbackQuery):
    await call.message.edit_text(SELECT_COEFFICIENT_TEXT, reply_markup=acceptance_coefficient_markup())


@dp.callback_query_handler(lambda c: c.data.startswith('coefficient_'))
async def process_coefficient_selection(query: types.CallbackQuery, state: FSMContext):
    coefficient = query.data.split('_')[1]
    await state.update_data(coefficient=coefficient)
    await dp.bot.answer_callback_query(query.id)
    await query.message.edit_text(SELECT_PERIOD_TEXT, reply_markup=period_selection_markup())


@dp.callback_query_handler(Text(startswith="period_"))
async def process_period_selection(query: types.CallbackQuery, state: FSMContext):
    await dp.bot.answer_callback_query(query.id)

    period = query.data.split('_')[-1]

    period_map = {
        "today": "Сегодня",
        "tomorrow": "Завтра",
        "3days": "3 дня",
        "week": "Неделя",
        "month": "Месяц"
    }

    selected_period = period_map.get(period, "Неизвестный период")
    await state.update_data(period=selected_period)

    await query.message.edit_text(SELECT_ALERT_TEXT, reply_markup=notification_count_markup())


@dp.callback_query_handler(lambda c: c.data in ['notify_once', 'notify_unlimited'])
async def process_notification_count_selection(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    try:
        user_data = await state.get_data()

        warehouse_ids = user_data.get("selected_warehouses", [])
        supply_types = user_data.get("selected_supply_types", [])
        coefficient = user_data.get("coefficient", "")

        if coefficient.startswith("<"):
            coefficient_value = float(coefficient[1:])  # Извлекаем число после '<'
            coefficient_range = f"<{coefficient_value}"  # Сохраняем как <value для диапазона
        else:
            coefficient_value = float(coefficient)  # Если не <, то просто сохраняем число
            coefficient_range = str(coefficient_value)

        supply_name_map = {
            "mono_pallets": 5,
            "boxes": 2,
            "super_safe": 6,
            "qr_supply": 7
        }

        boxTypeIDs = [supply_name_map.get(supply_type) for supply_type in supply_types if supply_type in supply_name_map]

        period_map = {
            "Сегодня": 1,
            "Завтра": 2,
            "3 дня": 3,
            "Неделя": 7,
            "Месяц": 30
        }

        warehouse_names = []
        for warehouse_id in warehouse_ids:
            warehouse = await redis_client.get_warehouse_by_id(warehouse_id)
            warehouse_names.append(warehouse['name'])

        supply_types_names = ', '.join(supply_type for supply_type in supply_types)

        period = period_map.get(user_data.get("period", "Неизвестный период"))

        notification_type = 0 if query.data == "notify_once" else 1

        for boxTypeID in boxTypeIDs:
            await redis_client.save_user_request(
                user_id=query.from_user.id,
                warehouse_ids=warehouse_ids,
                supply_types=supply_types,
                boxTypeID=boxTypeID,
                coefficient=coefficient_range,  # Сохраняем диапазон коэффициента
                period=period,
                status=notification_type  # Добавляем статус уведомления (0 или 1)
            )

        final_text = FINAL_NOTIFICATION_TEXT.format(
            warehouse_names=', '.join(warehouse_names),
            period=user_data.get('period', ''),
            supply_types_names=supply_types_names,
            coefficient=coefficient
        )

        bot_me = await dp.bot.get_me()
        await query.message.edit_text(final_text, reply_markup=start_bot_markup(bot_me.username), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя в Redis: {e}")
        await query.message.answer("Произошла ошибка при сохранении вашего запроса. Пожалуйста, попробуйте позже.")



