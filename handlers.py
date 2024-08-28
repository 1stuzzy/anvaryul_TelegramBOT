from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import dp, bot
from wb_api import get_warehouses, get_coefficients
from keyboards.pagination import create_pagination_keyboard
from keyboards.main_kbs import main_keyboard, menu_keyboard, alerts_keyboard, type_alert, warehouse_markup
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher import FSMContext
from loguru import logger
from states import Form
from db.models import Warehouse


@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state=FSMContext):
    await state.finish()
    await message.answer("Привет", reply_markup=main_keyboard())
    await message.answer("Нажмите на кнопку:", reply_markup=menu_keyboard())


@dp.message_handler(Text(equals="🔔 Оповещения"), state='*')
@dp.callback_query_handler(lambda c: c.data == 'alerts')
async def process_alerts(q):
    if isinstance(q, types.Message):
        chat_id = q.chat.id
        message_id = q.message_id
        await bot.send_message(chat_id,
                               "<b>🔔 Оповещения:</b>\n\n"
                               "<i>Получайте первыми уведомления о бесплатных слотах на складах Wildberries</i>\n",
                               reply_markup=alerts_keyboard())

    elif isinstance(q, types.CallbackQuery):
        chat_id = q.message.chat.id
        message_id = q.message.message_id
        await bot.answer_callback_query(q.id)

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>🔔 Оповещения:</b>\n\n"
                 "<i>Получайте первыми уведомления о бесплатных слотах на складах Wildberries</i>\n",
            reply_markup=alerts_keyboard()
        )


@dp.callback_query_handler(lambda c: c.data == 'create_alert')
async def process_alerts(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    try:
        await query.message.edit_text(
            text="<b>➕ Создание запроса:</b>\n\n"
                 "<i>Выберите тип оповощения:</i>",
            reply_markup=type_alert()
        )
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda c: c.data == 'default_alert')
async def process_alerts(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    print(f"Callback data received: {query.data}")

    user_id = query.from_user.id
    selected_warehouses = get_selected_warehouses(user_id)
    print(f"User {user_id} selected warehouses: {selected_warehouses}")

    try:
        await query.message.edit_text(
            text="<b>➕ Создание запроса:</b>\n\n"
                 "<i>Выберите склады (можно несколько):</i>",
            reply_markup=warehouse_markup(selected_warehouses)
        )
        print("Message edited successfully.")
    except MessageNotModified:
        print("Message was not modified.")
    except Exception as e:
        print(f"Error occurred: {e}")




user_selected_warehouses = {}


def get_selected_warehouses(user_id):
    return user_selected_warehouses.get(user_id, [])


def save_selected_warehouses(user_id, selected_warehouses):
    user_selected_warehouses[user_id] = selected_warehouses


@dp.callback_query_handler(lambda c: c.data.startswith('select_') or c.data.startswith('unselect_'))
async def process_warehouse_selection(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    selected_warehouses = get_selected_warehouses(user_id)

    warehouse_id = int(callback_query.data.split('_')[1])

    if callback_query.data.startswith('select_'):
        if warehouse_id not in selected_warehouses:
            selected_warehouses.append(warehouse_id)
    elif callback_query.data.startswith('unselect_'):
        if warehouse_id in selected_warehouses:
            selected_warehouses.remove(warehouse_id)

    save_selected_warehouses(user_id, selected_warehouses)

    # Обновляем клавиатуру
    markup = warehouse_markup(selected_warehouses)
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        reply_markup=markup)
    await bot.answer_callback_query(callback_query.id)


@dp.callback_query_handler(lambda c: c.data == 'premium_alert')
async def process_alerts(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    try:
        await query.message.edit_text(
            text="<b>💎 Опция 'Приоритетный поиск слотов':</b>",
            reply_markup=None
        )
    except MessageNotModified:
        pass


@dp.callback_query_handler(lambda c: c.data == 'my_alerts')
async def process_alerts(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    try:
        await query.message.edit_text(
            text="<b>🔍 Мои запросы:</b>",
            reply_markup=None
        )
    except MessageNotModified:
        pass






















@dp.message_handler(Text(equals="Оповещения"), state='*')
async def send_warehouses(message: types.Message, state: FSMContext):
    await state.finish()  # Завершаем любые предыдущие состояния
    warehouses = await get_warehouses()
    if warehouses:
        await message.answer("Выберите склад из списка ниже:", reply_markup=create_pagination_keyboard(warehouses, page=0))
        await Form.selecting_warehouses.set()  # Устанавливаем состояние выбора складов
    else:
        await message.answer("Не удалось получить список складов. Попробуйте позже.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('page_'), state=Form.selecting_warehouses)
async def process_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Обработка пагинации с данными: {callback_query.data}")
    page = int(callback_query.data.split('_')[1])
    warehouses = await get_warehouses()

    if warehouses:
        await bot.edit_message_reply_markup(callback_query.from_user.id, callback_query.message.message_id,
                                            reply_markup=create_pagination_keyboard(warehouses, page))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('select_'), state=Form.selecting_warehouses)
async def process_warehouse_selection(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Обработка выбора склада с данными: {callback_query.data}")
    warehouse_id, page = callback_query.data.split('_')[1], int(callback_query.data.split('_')[2])

    async with state.proxy() as data:
        if 'selected_warehouses' not in data:
            data['selected_warehouses'] = []
        if warehouse_id in data['selected_warehouses']:
            data['selected_warehouses'].remove(warehouse_id)
        else:
            data['selected_warehouses'].append(warehouse_id)

    warehouses = await get_warehouses()
    await bot.edit_message_reply_markup(
        callback_query.from_user.id,
        callback_query.message.message_id,
        reply_markup=create_pagination_keyboard(warehouses, page, data['selected_warehouses'])
    )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('continue_'), state=Form.selecting_warehouses)
async def process_continue(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Обработка продолжения с данными: {callback_query.data}")
    async with state.proxy() as data:
        selected_warehouses = data.get('selected_warehouses', [])

    if selected_warehouses:
        await bot.send_message(
            callback_query.from_user.id,
            f"Вы выбрали следующие склады: {', '.join(selected_warehouses)}.\nВыберите тип поставки:",
        )
        await Form.confirming_selection.set()  # Переход к следующему шагу


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('tariff_'), state=Form.confirming_selection)
async def process_tariff_selection(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Обработка выбора тарифа с данными: {callback_query.data}")
    tariff_data = callback_query.data.split('_')
    warehouse_id = int(tariff_data[1])
    supply_type = tariff_data[2]
    tariff = tariff_data[3]

    coefficients = await get_coefficients(warehouse_id)
    coef_str = ", ".join([f"{coef['date']}: {coef['coefficient']}" for coef in coefficients]) if coefficients else "Коэффициенты не найдены"

    await bot.send_message(
        callback_query.from_user.id,
        f"Вы выбрали поставку {supply_type} на склад {warehouse_id}.\n"
        f"Максимальный тариф приемки: {tariff}.\n"
        f"Коэффициенты: {coef_str}"
    )
    await state.finish()