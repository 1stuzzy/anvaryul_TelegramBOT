from loader import dp
from aiogram import types
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from html import escape
from loguru import logger
from data.texts import *
from data.keyboards.main_kbs import (main_keyboard, menu_keyboard, alerts_keyboard, type_alert,
                                     warehouse_markup, update_markup, supply_types_markup,
                                     acceptance_coefficient_markup, notification_count_markup,
                                     period_selection_markup, requests_keyboard, back_to_alerts_kb, back_btn, back_btn2)


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

        # Извлекаем данные из состояния
        warehouse_ids = user_data.get("selected_warehouses", [])
        supply_types = user_data.get("selected_supply_types", [])
        coefficient = user_data.get("coefficient", "")

        # Форматируем коэффициент
        coefficient_range = coefficient if not coefficient.startswith("<") else f"<{float(coefficient[1:])}"

        # Формируем строку с названиями типов поставок
        supply_types_names = ', '.join(SUPPLY_TYPE_RUS_MAP.get(st, st) for st in supply_types)

        # Карта периодов и их преобразование
        period_map = {"Сегодня": 1, "Завтра": 2, "3 дня": 3, "Неделя": 7, "Месяц": 30}
        period = user_data.get("period", "Неизвестный период")

        # Получение названий складов
        warehouse_names = []
        for wh_id in warehouse_ids:
            warehouse = await redis_client.get_warehouse_by_id(wh_id)
            if warehouse:
                warehouse_names.append(warehouse.get('name', ''))

        warehouse_names = ', '.join(warehouse_names)

        # Определение типа уведомлений
        notification_type = 0 if query.data == "notify_once" else 1

        # Объединяем все boxTypeID для типов поставок
        boxTypeIDs = [SUPPLY_NUM_MAP.get(st) for st in supply_types if st in SUPPLY_TYPE_RUS_MAP]

        # Сохраняем запрос только один раз с объединенными данными
        await redis_client.save_user_request(
            user_id=query.from_user.id,
            warehouse_ids=warehouse_ids,
            supply_types=supply_types,
            boxTypeID=','.join(boxTypeIDs),
            coefficient=coefficient_range,
            period=period,
            notify=notification_type
        )

        final_text = FINAL_NOTIFICATION_TEXT.format(
            warehouse_names=escape(warehouse_names),
            period=escape(period),
            supply_types_names=escape(supply_types_names),
            coefficient=escape(coefficient_range)
        )

        await query.message.edit_text(final_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя в Redis: {e}")
        await query.message.answer("Произошла ошибка при сохранении вашего запроса. Пожалуйста, попробуйте позже.")


@dp.callback_query_handler(lambda call: call.data == "my_requests")
async def handle_my_alerts(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    user_id = query.from_user.id

    try:
        user_requests = await redis_client.get_user(user_id)

        if not user_requests:
            await query.message.edit_text("У вас нет активных запросов.", reply_markup=alerts_keyboard())
            return

        await query.message.edit_text("Ваши активные запросы:", reply_markup=requests_keyboard(user_requests))

    except Exception:
        await query.message.edit_text("<b>🔔 Оповещения:</b>\n\n"
                                      "<i>Получайте первыми уведомления о бесплатных слотах на складах Wildberries</i>",
                                      reply_markup=back_to_alerts_kb())


@dp.callback_query_handler(lambda call: call.data.startswith("request_details_"))
async def handle_request_details(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    user_id = query.from_user.id

    try:
        request_index = int(query.data.split('_')[2]) - 1

        # Check for valid index
        if request_index < 0:
            await query.message.edit_text("Некорректный запрос. Попробуйте позже.", reply_markup=alerts_keyboard())
            return

        user_requests = await redis_client.get_user(user_id)

        if 0 <= request_index < len(user_requests):
            request = user_requests[request_index]

            warehouse_name = request.get('warehouse_name', 'Неизвестный склад')
            date = request.get('date', 'Неизвестная дата')
            supply_types = ', '.join(SUPPLY_TYPE_RUS_MAP.get(st, st) for st in request.get('supply_types', '').split(','))
            coefficient = request.get('coefficient', 'Неизвестный коэффициент')
            period = request.get('period', 'Неизвестный период')
            notify_id = request.get('notify', 'Неизвестный статус')
            notify = "Уведомления без ограничения" if notify_id == 0 else "До первого уведомления"

            details_text = (
                f"<b>📋 Запрос №{request_index + 1}:\n\n"
                f"🔹 Склад: <i>{warehouse_name}</i>\n"
                f"🔹 Дата: <i>{date}</i>\n"
                f"🔹 Тип поставки: <i>{supply_types}</i>\n"
                f"🔹 Коэффициент: <i>{coefficient}</i>\n"
                f"🔹 Период: <i>{period}</i>\n"
                f"🔹 Уведомления: <i>{notify}</i></b>\n"
            )

            await query.message.edit_text(details_text, reply_markup=back_btn(date))
        else:
            await query.message.edit_text("Запрос не найден.", reply_markup=alerts_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при получении подробной информации о запросе: {e}")
        await query.message.edit_text("Произошла ошибка при получении подробной информации. Попробуйте позже.",
                                      reply_markup=alerts_keyboard())


@dp.callback_query_handler(lambda call: call.data == "back_to_my_requests")
async def handle_back_to_my_requests(query: types.CallbackQuery, state: FSMContext):
    await handle_my_alerts(query, state)


@dp.callback_query_handler(lambda call: call.data == "back_to_requst")
async def handle_back_to_my_requests(query: types.CallbackQuery, state: FSMContext):
    await handle_my_alerts(query, state)


@dp.callback_query_handler(lambda call: call.data.startswith("stop_search_"))
async def handle_stop_search(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    user_id = query.from_user.id

    try:
        # Получаем дату из callback_data
        timestamp = query.data.split('_')[2]

        updated = await redis_client.delete_user_request(user_id, timestamp)

        if updated:
            await query.answer("Поиск успешно завершен.")
            await query.message.edit_reply_markup(reply_markup=back_btn2())
        else:
            await query.message.edit_text("Не удалось завершить поиск. Попробуйте позже.", reply_markup=alerts_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при завершении поиска: {e}")
        await query.message.edit_text("Произошла ошибка при завершении поиска. Попробуйте позже.",
                                      reply_markup=alerts_keyboard())


