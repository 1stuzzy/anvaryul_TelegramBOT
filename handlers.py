from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import dp, bot
from wb_api import get_warehouses
from keyboards.pagination import create_pagination_keyboard
from keyboards.main_kbs import main_keyboard
from aiogram.dispatcher.filters import Text


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Нажми на кнопку, чтобы получить список складов или найти склад.", reply_markup=main_keyboard())


@dp.message_handler(Text(equals="Получить список складов"))
async def send_warehouses(message: types.Message):
    warehouses = await get_warehouses()
    if warehouses:
        await message.answer("Выберите склад из списка ниже:", reply_markup=create_pagination_keyboard(warehouses, page=0))
    else:
        await message.answer("Не удалось получить список складов. Попробуйте позже.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('page_'))
async def process_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[1])
    warehouses = await get_warehouses()

    if warehouses:
        await bot.edit_message_reply_markup(callback_query.from_user.id, callback_query.message.message_id,
                                            reply_markup=create_pagination_keyboard(warehouses, page))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('warehouse_'))
async def process_warehouse_selection(callback_query: types.CallbackQuery):
    warehouse_id = callback_query.data.split('_')[1]
    warehouses = await get_warehouses()
    selected_warehouse = next((wh for wh in warehouses if str(wh['ID']) == warehouse_id), None)

    if selected_warehouse:
        # Создаем клавиатуру для выбора типа поставки
        supply_type_keyboard = InlineKeyboardMarkup(row_width=2)
        supply_type_keyboard.add(
            InlineKeyboardButton("Короб", callback_data=f"supply_type_Короб_{warehouse_id}_{selected_warehouse.get('name')}"),
            InlineKeyboardButton("Суперсейф", callback_data=f"supply_type_Суперсейф_{warehouse_id}_{selected_warehouse.get('name')}"),
            InlineKeyboardButton("Монопланета", callback_data=f"supply_type_Монопланета_{warehouse_id}_{selected_warehouse.get('name')}"),
            InlineKeyboardButton("QR-Поставка", callback_data=f"supply_type_QR_{warehouse_id}_{selected_warehouse.get('name')}")
        )

        await bot.send_message(
            callback_query.from_user.id,
            f"Выберите вид поставки для склада <b>{selected_warehouse.get('name', 'Нет данных')}</b>:",
            reply_markup=supply_type_keyboard,
            parse_mode='HTML'
        )
    else:
        await bot.send_message(callback_query.from_user.id, "Не удалось найти информацию о выбранном складе.")


# Хендлер для обработки выбора типа поставки
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('supply_type_'))
async def process_supply_type_selection(callback_query: types.CallbackQuery):
    supply_type_data = callback_query.data.split('_')
    supply_type = supply_type_data[2]
    warehouse_id = supply_type_data[3]
    warehouse_name = '_'.join(supply_type_data[4:])  # Склеиваем название склада, если оно содержит несколько слов

    # Создаем клавиатуру для выбора максимального тарифа
    tariff_keyboard = InlineKeyboardMarkup(row_width=2)
    tariff_keyboard.add(
        InlineKeyboardButton("Бесплатно", callback_data=f"tariff_Бесплатно_{warehouse_id}_{supply_type}_{warehouse_name}"),
        InlineKeyboardButton("MAX x1", callback_data=f"tariff_MAX_x1_{warehouse_id}_{supply_type}_{warehouse_name}"),
        InlineKeyboardButton("MAX x2", callback_data=f"tariff_MAX_x2_{warehouse_id}_{supply_type}_{warehouse_name}"),
        InlineKeyboardButton("MAX x3", callback_data=f"tariff_MAX_x3_{warehouse_id}_{supply_type}_{warehouse_name}"),
        InlineKeyboardButton("MAX x5", callback_data=f"tariff_MAX_x5_{warehouse_id}_{supply_type}_{warehouse_name}"),
        InlineKeyboardButton("MAX x6", callback_data=f"tariff_MAX_x6_{warehouse_id}_{supply_type}_{warehouse_name}")
    )

    await bot.send_message(
        callback_query.from_user.id,
        f"Вы выбрали {supply_type} для склада {warehouse_name.replace('_', ' ')}. Какой максимальный тариф приемки вас устроит?",
        reply_markup=tariff_keyboard
    )


# Хендлер для обработки выбора тарифа
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('tariff_'))
async def process_tariff_selection(callback_query: types.CallbackQuery):
    tariff_data = callback_query.data.split('_')
    tariff = tariff_data[1]
    warehouse_id = tariff_data[2]
    supply_type = tariff_data[3]
    warehouse_name = '_'.join(tariff_data[4:])  # Склеиваем название склада

    # Подтверждаем выбор пользователя
    await bot.send_message(
        callback_query.from_user.id,
        f"Вы выбрали поставку {supply_type} на склад {warehouse_name.replace('_', ' ')}.\n"
        f"Максимальный тариф приемки: {tariff}."
    )


# Хендлер для обработки выбора тарифа
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('tariff_'))
async def process_tariff_selection(callback_query: types.CallbackQuery):
    tariff_data = callback_query.data.split('_')
    tariff = tariff_data[1]
    warehouse_id = tariff_data[2]
    supply_type = tariff_data[3]

    # Получаем информацию о складе
    warehouses = await get_warehouses()
    selected_warehouse = next((wh for wh in warehouses if str(wh['ID']) == warehouse_id), None)

    if selected_warehouse:
        await bot.send_message(
            callback_query.from_user.id,
            f"Вы выбрали поставку {supply_type} на склад {selected_warehouse['name']}.\n"
            f"Максимальный тариф приемки: {tariff}."
        )
    else:
        await bot.send_message(callback_query.from_user.id, "Не удалось найти информацию о складе.")
