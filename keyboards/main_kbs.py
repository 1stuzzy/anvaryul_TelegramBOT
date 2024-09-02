from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified
from aiogram import types
from db.basefunctional import get_warehouses, init_redis
from loguru import logger
import asyncio


def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    alert_btn = KeyboardButton("🔔 Оповещения")
    markup.add(alert_btn)
    return markup


def menu_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(text="🔔 Оповещения", callback_data="alerts"),
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
    ]
    markup.add(*buttons)
    return markup


def alerts_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()

    markup.add(InlineKeyboardButton("❓ Как это работает?", callback_data="faq"))
    markup.add(InlineKeyboardButton("📑 Мои запросы", callback_data="my_alerts"))
    markup.insert(InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))

    return markup


def type_alert() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()

    markup.add(InlineKeyboardButton("🔍 Поиск слотов", callback_data="default_alert"))
    markup.add(InlineKeyboardButton("⭐️ Премиум поиск", callback_data="premium_alert"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))

    return markup


async def get_warehouses_markup():
    markup = InlineKeyboardMarkup()

    try:
        redis = await init_redis()
        warehouses = await get_warehouses(redis)
        for warehouse in warehouses:
            markup.add(InlineKeyboardButton(
                text=warehouse['name'],
                callback_data=f"warehouse_{warehouse['id']}"
            ))

    except Exception as e:
        logger.error(f"Ошибка при получении складов из Redis: {e}")
        return None

    return markup



async def warehouse_markup(selected_warehouses=None, page=0) -> InlineKeyboardMarkup:
    selected_warehouses = [str(id) for id in (selected_warehouses or [])]
    
    redis = await init_redis()
    warehouses = await get_warehouses(redis)
    
    max_items_per_page = 16
    total_warehouses = len(warehouses)
    total_pages = (total_warehouses + max_items_per_page - 1) // max_items_per_page

    start_index = page * max_items_per_page
    end_index = min(start_index + max_items_per_page, total_warehouses)

    markup = InlineKeyboardMarkup(row_width=2)

    for warehouse in warehouses[start_index:end_index]:
        is_selected = str(warehouse["id"]) in selected_warehouses
        text = f"✅ {warehouse['name']}" if is_selected else warehouse['name']
        callback_data = f"{'unselect' if is_selected else 'select'}_{warehouse['id']}_page_{page}"

        logger.debug(f"Warehouse: {warehouse['name']} - Selected: {is_selected}")  # Отладочный вывод

        if len(callback_data) <= 64:
            markup.insert(InlineKeyboardButton(text, callback_data=callback_data))

    # Навигационные кнопки
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_back_{page-1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_forward_{page+1}"))

    if navigation_buttons:
        markup.row(*navigation_buttons)

    if selected_warehouses:
        markup.add(InlineKeyboardButton("Продолжить ▶️", callback_data="continue"))

    markup.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="go_back"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )

    return markup



async def update_markup(message: types.Message, markup: InlineKeyboardMarkup):
    try:
        await message.edit_reply_markup(reply_markup=markup)
    except MessageNotModified:
        await message.delete()
        await message.answer("Обновлено:", reply_markup=markup)
    except Exception as e:
        logger.error(f"Ошибка при обновлении клавиатуры: {e}")





def supply_types_markup(selected_supply_types=None):
    """Создает клавиатуру для выбора типов поставок."""
    selected_supply_types = set(selected_supply_types or [])

    supply_types = [
        ("Короба", "boxes"),
        ("Монопаллеты", "mono_pallets"),
        ("Суперсейф", "super_safe"),
        ("QR-Поставка", "qr_supply")
    ]

    markup = InlineKeyboardMarkup(row_width=2)

    for name, value in supply_types:
        if value in selected_supply_types:
            button_text = f"✅ {name}"
            callback_data = f"unselecttype_{value}"
        else:
            button_text = name
            callback_data = f"selecttype_{value}"

        markup.insert(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    if selected_supply_types:
        markup.add(InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply"))

    markup.row(InlineKeyboardButton(text="↩️ Назад", callback_data="go_back"),
               InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return markup


def acceptance_coefficient_markup():
    buttons = [
        InlineKeyboardButton(text="0", callback_data="coefficient_0"),
        InlineKeyboardButton(text="<1", callback_data="coefficient_1"),
        InlineKeyboardButton(text="<2", callback_data="coefficient_2"),
        InlineKeyboardButton(text="<3", callback_data="coefficient_3"),
        InlineKeyboardButton(text="<4", callback_data="coefficient_4"),
        InlineKeyboardButton(text="<5", callback_data="coefficient_5"),
        InlineKeyboardButton(text="<6", callback_data="coefficient_6"),
        InlineKeyboardButton(text="<8", callback_data="coefficient_8"),
    ]

    markup = InlineKeyboardMarkup(row_width=4)
    markup.add(buttons[0], buttons[1], buttons[2], buttons[3])
    markup.add(buttons[4], buttons[5], buttons[6], buttons[7])
    markup.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="go_back"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return markup


def period_selection_markup():
    buttons = [
        InlineKeyboardButton(text="Сегодня", callback_data="period_today"),
        InlineKeyboardButton(text="Завтра", callback_data="period_tomorrow"),
        InlineKeyboardButton(text="3 дня", callback_data="period_3days"),
        InlineKeyboardButton(text="Неделя", callback_data="period_week"),
        InlineKeyboardButton(text="Месяц", callback_data="period_month"),
    ]
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    markup.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="go_back"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return markup


def notification_count_markup() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора количества уведомлений."""
    markup = InlineKeyboardMarkup(row_width=1)

    buttons = [
        InlineKeyboardButton(text="До первого уведомления", callback_data="notify_once"),
        InlineKeyboardButton(text="Без ограничений", callback_data="notify_unlimited")
    ]

    markup.add(*buttons)

    markup.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="go_back"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )

    return markup


def start_bot_markup(bot_name=None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для запуска бота."""
    markup = InlineKeyboardMarkup(row_width=1)

    buttons = [
        InlineKeyboardButton(text="Перейти и запустить бот", url=f"https://t.me/{bot_name}")
    ]
    markup.add(*buttons)

    return markup
