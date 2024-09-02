from aiogram import types
import aioredis
import asyncio
from loader import dp, bot
from keyboards.main_kbs import (main_keyboard, menu_keyboard, alerts_keyboard,
                                type_alert, warehouse_markup, period_selection_markup,
                                supply_types_markup, acceptance_coefficient_markup, notification_count_markup,
                                start_bot_markup)
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified, Throttled
from aiogram.dispatcher import FSMContext
from loguru import logger
from db.models import UserRequest
from db.basefunctional import get_warehouses, get_warehouse_name
from wb_api import add_notification_to_queue, init_redis


@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Привет", reply_markup=main_keyboard())
    await message.answer("Нажмите на кнопку:", reply_markup=menu_keyboard())


@dp.message_handler(Text(equals="🔔 Оповещения"), state='*')
@dp.callback_query_handler(lambda c: c.data == 'alerts')
async def process_alerts(q):
    chat_id, message_id = (q.chat.id, q.message_id) if isinstance(q, types.Message) else (q.message.chat.id, q.message.message_id)
    await bot.send_message(
        chat_id,
        "<b>🔔 Оповещения:</b>\n\n<i>Получайте первыми уведомления о бесплатных слотах на складах Wildberries</i>\n",
        reply_markup=alerts_keyboard()
    )


@dp.callback_query_handler(lambda c: c.data == 'create_alert')
async def process_create_alert(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    try:
        await query.message.edit_text("<b>➕ Создание запроса:</b>\n\n<i>Выберите тип оповощения:</i>", reply_markup=type_alert())
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda c: c.data == 'default_alert', state='*')
async def process_default_alert(query: types.CallbackQuery, state: FSMContext):
    await state.reset_state(with_data=True)
    await bot.answer_callback_query(query.id)
    await state.update_data(selected_warehouses=[])

    try:
        await query.message.edit_text("<b>➕ Создание запроса:</b>\n\n<i>Выберите склады (можно несколько):</i>",
                                      reply_markup=warehouse_markup([]))
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda call: call.data.startswith("page_"))
async def handle_page_callback(call: types.CallbackQuery, state: FSMContext):
    direction, page = call.data.split("_")[1], int(call.data.split("_")[2])
    user_data = await state.get_data()
    selected_warehouses = user_data.get("selected_warehouses", [])
    total_pages = (len(get_warehouses()) + 15) // 16
    if direction == "back" and page > 0:
        page -= 1
    elif direction == "forward" and page < total_pages - 1:
        page += 1
    else:
        await call.answer("Вы уже на первой/последней странице.", show_alert=True)
        return

    await update_markup(call.message, warehouse_markup(selected_warehouses, page))


@dp.callback_query_handler(lambda call: call.data.startswith(("select_", "unselect_")))
async def handle_select_callback(call: types.CallbackQuery, state: FSMContext):
    try:
        data_parts = call.data.split("_")
        action = data_parts[0]
        warehouse_id_str = data_parts[1]  # Это должен быть warehouse_id
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
            await update_markup(call.message, warehouse_markup(selected_warehouses=selected_warehouses, page=page))
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке callback-данных: {e}")



async def update_markup(message, markup):
    try:
        await message.edit_reply_markup(reply_markup=markup)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f"Ошибка при обновлении клавиатуры: {e}")


@dp.callback_query_handler(lambda call: call.data == "continue")
async def handle_continue_callback(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "<b>➕ Создание запроса:</b>\n\n"
        "<i>Выберите типы поставок (можно несколько):</i>",
        reply_markup=supply_types_markup()
    )


@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('selecttype_') or c.data.startswith('unselecttype_')))
async def process_supply_type_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    action, supply_type = callback_query.data.split('_', 1)

    user_data = await state.get_data()
    selected_supply_types = user_data.get("selected_supply_types", set())

    if action == "selecttype":
        selected_supply_types.add(supply_type)
    elif action == "unselecttype":
        selected_supply_types.discard(supply_type)

    await state.update_data(selected_supply_types=selected_supply_types)
    markup = supply_types_markup(selected_supply_types)

    await callback_query.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == "continue_supply")
async def handle_continue_callback(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(f"<b>➕ Создание запроса:</b>\n\n"
                                 f"<i>Выберите коэффициент приемки (например если выбрать 1, то система будет искать коэффициенты 1 и меньше):</i>",
                                 reply_markup=acceptance_coefficient_markup())


@dp.callback_query_handler(lambda c: c.data.startswith('coefficient_'))
async def process_coefficient_selection(callback_query: types.CallbackQuery, state: FSMContext):
    coefficient = callback_query.data.split('_')[1]
    await state.update_data(coefficient=coefficient)

    await callback_query.message.edit_reply_markup(reply_markup=period_selection_markup())


@dp.callback_query_handler(Text(startswith="period_"))
async def process_period_selection(query: types.CallbackQuery, state: FSMContext):
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

    await query.message.edit_text(f"<b>➕ Создание запроса:</b>\n\n"
                                  f"<i>Сколько раз вас уведомить? (Например если выбрать до первого уведомления, то система пришлёт первый подходящий под ваши параметры слот и всё)</i>",
                                  reply_markup=notification_count_markup())


@dp.callback_query_handler(lambda c: c.data in ['notify_once', 'notify_unlimited'])
async def process_notification_count_selection(query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    # Формируем строку для отображения пользователю
    warehouse_names = ', '.join(
        get_warehouse_name(int(warehouse_id)) for warehouse_id in user_data.get("selected_warehouses", [])
    )

    # Преобразуем типы поставок
    supply_type_map = {
        "qr_supply": "QR-Поставка",
        "boxes": "Короба",
        "mono_pallets": "Монопаллеты",
        "super_safe": "Суперсейф"
    }
    selected_supply_types = ', '.join(
        supply_type_map.get(supply_type, supply_type) for supply_type in user_data.get("selected_supply_types", [])
    )

    coefficient = user_data.get("coefficient", "")

    # Преобразование периода в числовое значение
    period_map = {
        "Сегодня": 1,
        "Завтра": 2,
        "3 дня": 3,
        "Неделя": 7,
        "Месяц": 30
    }
    period = period_map.get(user_data.get("period", ""), 0)

    # Определяем тип уведомления: 0 - До первого уведомления, 1 - Без ограничений
    notification_type = 0 if query.data == "notify_once" else 1

    # Сохраняем данные в базу
    UserRequest.create(
        user_id=query.from_user.id,
        warehouse_ids=','.join(map(str, user_data.get("selected_warehouses", []))),  # Сохраняем warehouse_id
        supply_types=','.join(user_data.get("selected_supply_types", [])),
        coefficient=coefficient,
        period=period,
        notification_type=notification_type
    )

    # Формируем текст уведомления
    final_text = (
        "🚨 <b>ВНИМАНИЕ ВАЖНО!</b>\n\n"
        "<b>Активирование запроса:</b>\n\n"
        f"Запрос создан. Но не активирован!\n"
        f"Ваш запрос: {warehouse_names} / {user_data.get('period', '')} / {selected_supply_types} / меньше {coefficient}\n\n"
        "Уведомления о найденных слотах будут приходить в специальный бот для уведомлений (не в основной бот☝️)\n"
        "На каждый запрос о поиске, системой может быть назначен разный бот☝️!  При этом бот каждый раз нужно запустить!\n\n"
        "☝️☝️☝️ <b>ДЛЯ ЗАПУСКА ПОИСКА, НУЖНО НАЖАТЬ КНОПКУ НИЖЕ И В ОТКРЫВШЕМСЯ БОТЕ НАЖАТЬ КНОПКУ СТАРТ!</b>\n\n"
        "Только тогда система начнёт искать Вам слоты☝️\n\n"
        "УВЕДОМЛЕНИЯ БУДУТ ПРИХОДИТЬ ИМЕННО ОТТУДА! ИЗ ТОГО БОТА!\n\n"
        "НАЖАТЬ КНОПКУ ПЕРЕЙТИ И ЗАПУСТИТЬ и далее в боте запустить бота!\n"
        "⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️"
    )

    redis = await init_redis()  # Инициализация Redis, если не выполнена ранее
    await add_notification_to_queue(redis, query.from_user.id, final_text)

    bot_me = await dp.bot.get_me()
    await query.message.edit_text(final_text, reply_markup=start_bot_markup(bot_me.username))
