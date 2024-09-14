from aiogram import types
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageNotModified

from loguru import logger
from html import escape

from loader import config, dp
from data import texts, keyboards
from database.redis_base import RedisClient
from database import postgre_base

from functions import executional
from utils.datefunc import calculate_dates

from handlers.subscription import process_subscription


redis_client = RedisClient(redis_url=config.redis_url)


async def handle_my_requests(query: types.CallbackQuery):
    await query.answer()
    user_requests = await redis_client.get_user_requests(query.from_user.id)
    if not user_requests:
        await query.message.edit_text(texts.active_request_text,
                                      reply_markup=keyboards.close_btn())
        await query.answer(texts.requests_not_exists)
    else:
        await query.message.edit_text(texts.active_request_text,
                                      reply_markup=await keyboards.requests_keyboard(user_requests,
                                                                                     redis_client))


async def handle_request_details(query: types.CallbackQuery):
    await query.answer()
    try:
        request_index = int(query.data.split('_')[2]) - 1
        if request_index < 0:
            await query.answer(texts.incorrect_request_text, show_alert=True)
            return

        user_requests = await redis_client.get_user_requests(query.from_user.id)

        if 0 <= request_index < len(user_requests):
            request = user_requests[request_index]

            number = request_index + 1

            warehouse_ids = request.get('warehouse_ids', '').split(',')
            warehouse_names = [await redis_client.get_warehouse_name(warehouse_id) for warehouse_id in warehouse_ids]

            start_date = request.get('start_date')
            end_date = request.get('end_date')

            boxTypeID = request.get('boxTypeID')
            supply_type = executional.get_supply_name(boxTypeID)

            details_message = texts.details_text.format(
                number=number,
                warehouse_name=', '.join(warehouse_names),
                date=start_date,
                supply_type=supply_type,
                coefficient=request.get('coefficient'),
                period=f'{start_date} - {end_date}',
                notify_type='До первого совпадения' if request.get('notify_until_first', 'False').lower() == 'true'
                else 'Без ограничений'
            )

            await query.message.edit_text(details_message,
                                          reply_markup=keyboards.back_btn(request.get('request_id'),
                                                                          request.get('status_request'))
                                          )
        else:
            await query.answer(texts.request_not_exists, show_alert=True)

    except Exception as e:
        logger.error(f"Error getting request details: {e}")
        await query.answer(texts.unknown_error_text, show_alert=True)


async def process_create_alert(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    redis_client = query.bot.get('redis_client')
    await state.reset_state(with_data=True)
    await state.update_data(selected_warehouses=[])

    is_subscribed = await postgre_base.check_subscription(query.from_user.id)

    try:
        if is_subscribed:
            markup = await keyboards.warehouse_markup(redis_client, [])
            await query.message.edit_text(texts.select_warehouse_text, reply_markup=markup)
        else:
            await process_subscription(query, state)
    except MessageNotModified:
        pass


async def handle_select_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    redis_client = call.bot.get('redis_client')
    data_parts = call.data.split("_")
    if len(data_parts) < 2:
        return

    action = data_parts[0]
    warehouse_id_str = data_parts[1]

    if not warehouse_id_str.isdigit():
        return

    warehouse_id = int(warehouse_id_str)
    user_data = await state.get_data()
    selected_warehouses = user_data.get("selected_warehouses", [])

    if action == "select" and warehouse_id not in selected_warehouses:
        selected_warehouses.append(warehouse_id)
    elif action == "unselect" and warehouse_id in selected_warehouses:
        selected_warehouses.remove(warehouse_id)

    await state.update_data(selected_warehouses=selected_warehouses)

    updated_markup = await keyboards.warehouse_markup(
        redis_client=redis_client,
        selected_warehouses=selected_warehouses,
    )
    await keyboards.update_markup(call.message, updated_markup)


async def handle_continue_supply(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(texts.select_supply_text,
                                 reply_markup=keyboards.supply_types_markup())


async def process_supply_type_selection(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    action, type_id_str = query.data.split('_', 1)
    type_id = int(type_id_str)

    user_data = await state.get_data()
    selected_supply_types = user_data.get("selected_supply_types", set())

    if action == "selecttype":
        selected_supply_types.add(type_id)
    elif action == "unselecttype":
        selected_supply_types.discard(type_id)

    await state.update_data(selected_supply_types=selected_supply_types)
    await query.message.edit_reply_markup(reply_markup=keyboards.supply_types_markup(selected_supply_types))


async def handle_continue_coeff(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(texts.select_coefficient_text,
                                 reply_markup=keyboards.acceptance_coefficient_markup())


async def process_coefficient_selection(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    coefficient = query.data.split('_')[1]
    await state.update_data(coefficient=coefficient)
    await query.answer(query.id)
    await query.message.edit_text(texts.select_period_text,
                                  reply_markup=keyboards.period_selection_markup())


async def process_period_selection(query: types.CallbackQuery, state: FSMContext):
    await query.answer()

    period_key = query.data.split('_')[-1]
    selected_period_text, days_to_add = texts.period_map.get(period_key)
    await state.update_data(period=selected_period_text, days_to_add=days_to_add)

    await query.message.edit_text(texts.select_alert_text,
                                  reply_markup=keyboards.notification_count_markup())


async def process_create_notification(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    redis_client = query.bot.get('redis_client')
    notification_service = query.bot.get('notification_service')
    try:
        user_data = await state.get_data()

        warehouse_ids = user_data.get("selected_warehouses", [])
        coefficient = user_data.get("coefficient", "")
        days_to_add = user_data.get("days_to_add", 0)

        start_date, end_date = calculate_dates(days_to_add)

        coefficient_range = coefficient if coefficient and not coefficient.startswith("<") else f"<{float(coefficient[1:])}"

        warehouse_names = []
        for wh_id in warehouse_ids:
            warehouse = await redis_client.get_warehouse_by_id(wh_id)
            if warehouse:
                warehouse_names.append(warehouse.get('name', 'Неизвестный склад'))

        warehouse_names = ', '.join(warehouse_names)
        notification_type = 0 if query.data == "notify_once" else 1

        notify_until_first = notification_type == 0

        selected_supply_types = user_data.get("selected_supply_types", [])

        supply = ', '.join([name for name, (_, type_id) in texts.types_map.items() if type_id in selected_supply_types])

        box_id = [str(type_id) for _, (_, type_id) in texts.types_map.items() if type_id in selected_supply_types]

        await redis_client.save_request(
            user_id=query.from_user.id,
            warehouse_ids=warehouse_ids,
            boxTypeID=','.join(box_id),
            coefficient=coefficient_range,
            start_date=start_date,
            end_date=end_date,
            status_request=True,
            notify_until_first=notify_until_first
        )

        await notification_service.start_all_active_requests()

        coefficient_sign = "<" if coefficient_range.startswith('<') and coefficient_range != "0" else ""

        await query.message.edit_text(texts.notification_text.format(
            warehouse_names=escape(warehouse_names or ""),
            supply=escape(supply or ""),
            coefficient=escape(coefficient_sign + (coefficient_range.lstrip('<') if coefficient_range else "")),
            start_date=escape(start_date),
            end_date=escape(end_date)
        ))

    except Exception as e:
        logger.error(f"Ошибка при сохранении запроса пользователя в Redis: {e}")
        await query.message.answer("Произошла ошибка при сохранении вашего запроса. Пожалуйста, попробуйте позже.")


async def stop_search_callback_handler(query: types.CallbackQuery, state: FSMContext):
    """Обработчик для завершения поиска по нажатию кнопки."""
    try:
        # Извлекаем request_id из callback_data
        request_id = query.data.split("_")[2]
        user_id = query.from_user.id

        # Получаем экземпляр NotificationService из бота
        notification_service = query.bot.get('notification_service')

        # Останавливаем поиск
        await notification_service.stop_search(user_id, request_id)

        redis_client = query.bot.get('redis_client')
        await redis_client.stop_request(user_id, request_id)

        await handle_my_requests(query)
        logger.info(f"Поиск для пользователя {user_id} с запросом {request_id} был завершен.")

    except Exception as e:
        logger.error(f"Ошибка при завершении поиска для пользователя {user_id} с запросом {request_id}: {e}")
        await query.message.edit_text("❌ Произошла ошибка при завершении поиска. Попробуйте еще раз.", reply_markup=None)


def register_request_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(handle_request_details, lambda call: call.data.startswith("request_details_"))
    dp.register_callback_query_handler(handle_my_requests, lambda call: call.data == "my_requests")
    dp.register_callback_query_handler(process_create_alert, lambda call: call.data == "create_alert")
    dp.register_callback_query_handler(handle_select_callback, lambda call: call.data.startswith(("select_", "unselect_")))
    dp.register_callback_query_handler(handle_continue_supply, lambda call: call.data == "continue_supply")
    dp.register_callback_query_handler(process_supply_type_selection, lambda call: call.data.startswith(("selecttype_", "unselecttype_")))
    dp.register_callback_query_handler(handle_continue_coeff, lambda call: call.data == "continue_supply_coeff")
    dp.register_callback_query_handler(process_coefficient_selection, lambda query: query.data.startswith("coefficient_"))
    dp.register_callback_query_handler(process_period_selection, lambda call: call.data.startswith("period_"))
    dp.register_callback_query_handler(process_create_notification, lambda call: call.data in ["notify_once",
                                                                                               "notify_unlimited"])
    dp.register_callback_query_handler(stop_search_callback_handler, lambda call: call.data.startswith("stop_search_"))

