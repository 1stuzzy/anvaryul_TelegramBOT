from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from peewee import DoesNotExist
from db.models import Warehouse
from db.basefunctional import get_warehouses
from loguru import logger


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
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="back_menu"))

    return markup


def type_alert() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()

    markup.add(InlineKeyboardButton("🔍 Поиск слотов", callback_data="default_alert"))
    markup.add(InlineKeyboardButton("⭐️ Премиум поиск", callback_data="premium_alert"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="back_menu"))

    return markup


def get_warehouses_markup():
    markup = InlineKeyboardMarkup()

    try:
        warehouses = Warehouse.select()
        for warehouse in warehouses:
            markup.add(InlineKeyboardButton(
                text=warehouse.name,
                callback_data=f"warehouse_{warehouse.warehouse_id}"
            ))

    except DoesNotExist:
        logger.error("Склады не найдены в базе данных.")
        return None

    return markup


def warehouse_markup(selected_warehouses=None, page=0) -> InlineKeyboardMarkup:
    """Создать разметку клавиатуры с названиями складов."""
    if selected_warehouses is None:
        selected_warehouses = []

    max_items_per_page = 16
    markup = InlineKeyboardMarkup(row_width=2)

    # Получаем список складов из базы данных
    warehouses = get_warehouses()

    # Логирование для проверки полученных складов
    if not warehouses:
        print("No warehouses found.")
    else:
        print(f"Warehouses found: {warehouses}")

    # Создаем кнопки для каждого склада
    for warehouse in warehouses:
        if warehouse["id"] in selected_warehouses:
            text = f"✅ {warehouse['name']}"
            callback_data = f"unselect_{warehouse['id']}"
        else:
            text = warehouse['name']
            callback_data = f"select_{warehouse['id']}"

        # Логирование для проверки создания кнопок
        print(f"Adding button: {text} with callback_data: {callback_data}")
        markup.add(InlineKeyboardButton(text, callback_data=callback_data))

    # Пагинация (если необходимо)
    total_warehouses = len(warehouses)
    total_pages = (total_warehouses + max_items_per_page - 1) // max_items_per_page

    if page > 0:
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        markup.add(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page + 1}"))

    # Кнопка "Продолжить" отображается, если выбран хотя бы один элемент
    if selected_warehouses:
        markup.add(InlineKeyboardButton("Продолжить", callback_data="continue"))

    return markup