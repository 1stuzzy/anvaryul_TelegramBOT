import aioredis
import asyncio
from aiogram import types
from loader import dp, bot
from loguru import logger
from wb_api import add_notification_to_queue, init_redis
from db.basefunctional import get_warehouses, save_user_request_to_redis, get_warehouse_by_id
from keyboards.main_kbs import (
    main_keyboard, menu_keyboard, alerts_keyboard,
    type_alert, warehouse_markup, period_selection_markup,
    supply_types_markup, acceptance_coefficient_markup, notification_count_markup,
    start_bot_markup, update_markup
)
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified, Throttled
from aiogram.dispatcher import FSMContext



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
                                      reply_markup=await warehouse_markup([]))
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda call: call.data.startswith("page_"))
async def handle_page_callback(call: types.CallbackQuery, state: FSMContext):
    redis = await init_redis()
    direction, page = call.data.split("_")[1], int(call.data.split("_")[2])
    user_data = await state.get_data()
    selected_warehouses = user_data.get("selected_warehouses", [])

    all_warehouses = await get_warehouses(redis)
    total_pages = (len(all_warehouses) + 15) // 16
    
    if direction == "back" and page > 0:
        page -= 1
    elif direction == "forward" and page < total_pages - 1:
        page += 1
    else:
        await call.answer("Вы уже на первой/последней странице.", show_alert=True)
        return

    # Важно: используем await для вызова асинхронной функции
    await update_markup(call.message, await warehouse_markup(selected_warehouses, page))



@dp.callback_query_handler(lambda call: call.data.startswith(("select_", "unselect_")))
async def handle_select_callback(call: types.CallbackQuery, state: FSMContext):
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

            # Добавление или удаление склада в зависимости от действия
            if action == "select" and warehouse_id not in selected_warehouses:
                selected_warehouses.append(warehouse_id)
            elif action == "unselect" and warehouse_id in selected_warehouses:
                selected_warehouses.remove(warehouse_id)

            # Обновляем состояние выбранных складов в хранилище состояния
            await state.update_data(selected_warehouses=selected_warehouses)

            # Отладочный вывод для проверки состояния выбранных складов
            logger.debug(f"Selected warehouses: {selected_warehouses}")

            # Обновление клавиатуры
            updated_markup = await warehouse_markup(selected_warehouses=selected_warehouses, page=page)
            await update_markup(call.message, updated_markup)
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке callback-данных: {e}")




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
    try:
        # Получаем данные пользователя из состояния
        user_data = await state.get_data()

        # Инициализируем соединение с Redis
        redis = await init_redis()

        # Получаем идентификаторы складов и типы поставок из данных состояния
        warehouse_ids = user_data.get("selected_warehouses", [])
        supply_types = user_data.get("selected_supply_types", [])
        coefficient = user_data.get("coefficient", "")

        # Карта для преобразования типов поставок в человекочитаемый вид
        supply_name_map = {
            "mono_pallets": "Монопаллеты",
            "boxes": "Короба",
            "super_safe": "Суперсейф",
            "qr_supply": "QR-Поставка"
        }

        # Карта для преобразования периода в дни
        period_map = {
            "Сегодня": 1,
            "Завтра": 2,
            "3 дня": 3,
            "Неделя": 7,
            "Месяц": 30
        }

        # Преобразование идентификаторов складов в их названия
        warehouse_names = []
        for warehouse_id in warehouse_ids:
            warehouse = await get_warehouse_by_id(redis, warehouse_id)
            warehouse_names.append(warehouse['name'])

        # Преобразуем типы поставок в текстовые названия
        supply_types_names = ', '.join(supply_name_map.get(supply_type, supply_type) for supply_type in supply_types)

        # Получаем период в человекочитаемом виде
        period = period_map.get(user_data.get("period", "Неизвестный период"))

        # Определяем тип уведомления
        notification_type = 0 if query.data == "notify_once" else 1

        # Сохраняем запрос пользователя в Redis
        await save_user_request_to_redis(
            redis,
            user_id=query.from_user.id,
            warehouse_ids=','.join(map(str, warehouse_ids)),
            supply_types=','.join(supply_types),
            coefficient=coefficient,
            period=period,
            notification_type=notification_type
        )

        # Формируем финальный текст для отображения пользователю
        final_text = (
            "🚨 <b>ВНИМАНИЕ ВАЖНО!</b>\n\n"
            "<b>Активирование запроса:</b>\n\n"
            f"Запрос создан. Но не активирован!\n"
            f"Ваш запрос: {', '.join(warehouse_names)} / {user_data.get('period', '')} / {supply_types_names} / меньше {coefficient}\n\n"
            "Уведомления о найденных слотах будут приходить в специальный бот для уведомлений (не в основной бот☝️)\n"
            "На каждый запрос о поиске, системой может быть назначен разный бот☝️!  При этом бот каждый раз нужно запустить!\n\n"
            "☝️☝️☝️ <b>ДЛЯ ЗАПУСКА ПОИСКА, НУЖНО НАЖАТЬ КНОПКУ НИЖЕ И В ОТКРЫВШЕМСЯ БОТЕ НАЖАТЬ КНОПКУ СТАРТ!</b>\n\n"
            "Только тогда система начнёт искать Вам слоты☝️\n\n"
            "УВЕДОМЛЕНИЯ БУДУТ ПРИХОДИТЬ ИМЕННО ОТТУДА! ИЗ ТОГО БОТА!\n\n"
            "НАЖАТЬ КНОПКУ ПЕРЕЙТИ И ЗАПУСТИТЬ и далее в боте запустить бота!\n"
            "⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️"
        )

        # Получаем информацию о боте и отправляем пользователю сообщение с финальным текстом
        bot_me = await dp.bot.get_me()
        await query.message.edit_text(final_text, reply_markup=start_bot_markup(bot_me.username))

    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя в Redis: {e}")
        await query.message.answer("Произошла ошибка при сохранении вашего запроса. Пожалуйста, попробуйте позже.")

