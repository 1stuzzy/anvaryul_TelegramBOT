import random
from loader import dp, config
from aiogram import types
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from html import escape
from loguru import logger
from data.texts import *
from db import basefunctional
from db.models import User
from data.keyboards.main_kbs import (main_keyboard, menu_keyboard, alerts_keyboard, type_alert,
                                     warehouse_markup, update_markup, supply_types_markup,
                                     acceptance_coefficient_markup, notification_count_markup,
                                     period_selection_markup, requests_keyboard, back_to_alerts_kb, back_btn, back_btn2,
                                     support_keyboard, back_btn3, subscribe_kb, subscribe_duration_keyboard)
from functions.freekassa_api import FreeKassaApi

freekassa_api = FreeKassaApi(
    merchant_id=123123,
    first_secret=123123,
    second_secret=123123,
    wallet_id=123123,
    wallet_api_key=config.freekassa_token
)

@dp.message_handler(Text(equals="💠 Главное меню"), state='*')
@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    
    user_id = message.from_user.id
    name = message.from_user.full_name
    username = message.from_user.username
    
    try:
        logger.debug(f"[{user_id}:{name}], in base info updated")
        user = User.get(User.user_id == user_id)
        if user.name != name or user.username != username:
            user.name = name
            user.username = username
            user.save()

    except User.DoesNotExist:
        logger.debug(f"[{user_id}:{name}], first time /start to bot")           
        await basefunctional.create_user(
            user_id=user_id,
            name=name,
            username=username
        )

    await message.answer_sticker(START_TEXT, reply_markup=main_keyboard())
    await message.answer(ALERTS_TEXT, reply_markup=menu_keyboard())


@dp.message_handler(Text(equals="👨‍💻 Техническая поддержка"), state='*')
async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    support = config.support
    await message.answer(TECH_SUPPORT_TEXT, reply_markup=support_keyboard(support))


@dp.callback_query_handler(lambda call: call.data == 'faq')
async def process_faq(query, state=FSMContext):
    await state.finish()
    await query.message.edit_text(FAQ_TEXT, reply_markup=back_btn3())


@dp.callback_query_handler(lambda call: call.data == 'subscribe' or call.data == 'not_subscribe')
async def process_subscribe(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if query.data == 'subscribe':
        await query.message.edit_text(SUBSCRIBE_TEXT, reply_markup=subscribe_kb())
    else:
        await query.answer("⚠️ Для доступа к этому разделу вам необходимо оформить подписку.", show_alert=True)
        await query.message.edit_text(SUBSCRIBE_TEXT, 
                                      reply_markup=subscribe_kb())


@dp.callback_query_handler(lambda call: call.data == 'go_to_subscribe', state='*')
async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text("Выберите срок подписки:", reply_markup=subscribe_duration_keyboard())

# Обработчик для выбора срока подписки
@dp.callback_query_handler(Text(startswith="subscribe_"), state='*')
async def handle_subscription_duration(query: types.CallbackQuery, state: FSMContext):
    await state.finish()

    duration = query.data.split('_')[1]  # Получаем выбранный срок

    # Генерация рандомного order_id
    order_id = random.randint(100000, 999999)  # Генерация случайного числа от 100000 до 999999

    # Определяем стоимость в зависимости от выбранного срока
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

    # Генерация ссылки на оплату
    payment_link = freekassa_api.generate_payment_link(
        order_id=order_id,  # Используем сгенерированный случайный order_id
        summ=amount,
        description=description
    )

    # Отправка ссылки пользователю
    await query.message.edit_text(
        f"Для оплаты подписки на выбранный срок перейдите по ссылке: [Оплатить]({payment_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


@dp.callback_query_handler(lambda call: call.data == 'create_alert', state='*')
async def process_create_alert(query: types.CallbackQuery, state=FSMContext):
    redis_client = query.bot.get('redis_client')
    await state.reset_state(with_data=True)

    await state.update_data(selected_warehouses=[])

    is_subscribed = await basefunctional.check_subscription(query.from_user.id)

    try:
        if is_subscribed:
            markup = await warehouse_markup(redis_client, [])
            await query.message.edit_text(SELECT_WAREHOUSE_TEXT, reply_markup=markup)
        else:
            await process_subscribe(query, state)

    except MessageNotModified:
        pass

    if query.data == 'premium_alert':
        await query.answer('🛠 В разработке...')


@dp.callback_query_handler(lambda call: call.data == "back_menu")
async def process_go_back(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer_sticker(START_TEXT, reply_markup=main_keyboard())
    await query.message.answer(
        MAIN_MENU_TEXT,
        reply_markup=menu_keyboard()
    )
    await query.answer()


@dp.callback_query_handler(lambda call: call.data == "cancel")
async def process_cancel(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer_sticker(START_TEXT, reply_markup=main_keyboard())
    await query.message.answer(
        MAIN_MENU_TEXT,
        reply_markup=menu_keyboard()
    )
    await query.answer()


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

        coefficient_range = coefficient if not coefficient.startswith("<") else f"<{float(coefficient[1:])}"

        supply_types_names = ', '.join(SUPPLY_TYPE_RUS_MAP.get(st, st) for st in supply_types)

        period = user_data.get("period", "Неизвестный период")

        warehouse_names = []
        for wh_id in warehouse_ids:
            warehouse = await redis_client.get_warehouse_by_id(wh_id)
            if warehouse:
                warehouse_names.append(warehouse.get('name', ''))

        warehouse_names = ', '.join(warehouse_names)

        notification_type = 0 if query.data == "notify_once" else 1

        boxTypeIDs = [SUPPLY_NUM_MAP.get(st) for st in supply_types if st in SUPPLY_TYPE_RUS_MAP]

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

        final_text = FINAL_NOTIFICATION_TEXT.format(
            warehouse_names=escape(warehouse_names),
            period=escape(period),
            supply_types_names=escape(supply_types_names),
            coefficient=escape(coefficient_sign + coefficient_range.lstrip('<'))
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
            await query.answer("У вас нет активных запросов.", show_alert=True)
            return

        await query.message.edit_text("<b>📃 Ваши активные запросы:</b>", reply_markup=requests_keyboard(user_requests))

    except Exception:
        await query.message.edit_text(ALERTS_TEXT,
                                      reply_markup=back_to_alerts_kb())


@dp.callback_query_handler(lambda call: call.data.startswith("request_details_"))
async def handle_request_details(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    user_id = query.from_user.id

    try:
        request_index = int(query.data.split('_')[2]) - 1

        if request_index < 0:
            await query.answer("Некорректный запрос. Попробуйте позже.")
            return

        user_requests = await redis_client.get_user(user_id)

        if 0 <= request_index < len(user_requests):
            request = user_requests[request_index]

            warehouse_name = request.get('warehouse_name', 'Неизвестный склад')
            date = request.get('date', 'Неизвестная дата')
            supply_types = ', '.join(SUPPLY_TYPE_RUS_MAP.get(st, st) for st in request.get('supply_types', '').split(','))
            coefficient = request.get('coefficient', 'Неизвестный коэффициент')
            period = request.get('period', 'Неизвестный период')
            notify_id = int(request.get('notify', 'Неизвестный статус'))
            notify = "Уведомления без ограничения" if notify_id == 1 else "До первого уведомления"
            status_request = request.get('status_request')

            details_text = (
                f"<b>📋 Запрос №{request_index + 1}:\n\n"
                f"🔹 Склад: <i>{warehouse_name}</i>\n"
                f"🔹 Дата: <i>{date}</i>\n"
                f"🔹 Тип поставки: <i>{supply_types}</i>\n"
                f"🔹 Коэффициент: <i>{coefficient}</i>\n"
                f"🔹 Период: <i>{period}</i>\n"
                f"🔹 Уведомления: <i>{notify}</i></b>\n"
            )

            await query.message.edit_text(details_text, reply_markup=back_btn(date, status_request))
        else:
            await query.answer("Запрос не найден.")

    except Exception as e:
        logger.error(f"Ошибка при получении подробной информации о запросе: {e}")
        await query.answer("Произошла ошибка при получении подробной информации. Попробуйте позже.")



@dp.callback_query_handler(lambda call: call.data == "back_to_my_requests")
async def handle_back_to_my_requests(query: types.CallbackQuery, state: FSMContext):
    await handle_my_alerts(query, state)


@dp.callback_query_handler(lambda call: call.data == "back_to_request")
async def handle_back_to_my_requests(query: types.CallbackQuery, state: FSMContext):
    await handle_my_alerts(query, state)


@dp.callback_query_handler(lambda call: call.data.startswith("stop_search_"))
async def handle_stop_search(query: types.CallbackQuery, state: FSMContext):
    redis_client = query.bot.get('redis_client')
    user_id = query.from_user.id

    try:
        timestamp = query.data.split('_')[2]

        # Попытка получить данные запроса из Redis
        request_key = f"user_request:{user_id}:{timestamp}"
        request_data = await redis_client.redis.hgetall(request_key)

        if not request_data:
            await query.message.edit_text("Запрос не найден.", reply_markup=alerts_keyboard())
            return

        # Проверка текущего статуса запроса
        status_request = request_data.get('status_request', 'false')

        if status_request == 'false':
            await query.answer("Поиск уже был завершен.")
            return

        # Обновление статуса запроса на 'false' в Redis
        updated = await redis_client.stop_user_request(user_id, timestamp)

        if updated:
            await query.answer("Поиск успешно завершен.")
            await query.message.edit_reply_markup(reply_markup=back_btn(timestamp, 'false'))
        else:
            await query.answer("Не удалось завершить поиск. Попробуйте позже.")
    
    except Exception as e:
        logger.error(f"Ошибка при завершении поиска: {e}")
        await query.message.edit_text("Произошла ошибка при завершении поиска. Попробуйте позже.",
                                      reply_markup=alerts_keyboard())




