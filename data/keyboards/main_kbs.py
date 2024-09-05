from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified
from aiogram import types
from loguru import logger


def main_keyboard():
    """Создает основную клавиатуру с кнопкой оповещений."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    main_btn = KeyboardButton("💠 Главное меню")
    support_btn = KeyboardButton("👨‍💻 Техническая поддержка")
    markup.add(main_btn)
    markup.add(support_btn)
    return markup


def menu_keyboard():
    """Создает клавиатуру меню с кнопками оповещений и FAQ."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("❓ Как это работает?", callback_data="faq"))
    markup.add(InlineKeyboardButton("📑 Активные запросы", callback_data="my_requests"))
    markup.insert(InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert"))
    return markup


def support_keyboard(support):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📩 Написать сообщение", url=f"t.me/{support}"))
    return markup


def alerts_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для оповещений с опциями управления запросами."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❓ Как это работает?", callback_data="faq"))
    markup.add(InlineKeyboardButton("📑 Активные запросы", callback_data="my_requests"))
    markup.insert(InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert"))
    return markup


def back_to_alerts_kb() -> InlineKeyboardMarkup:
    """Создает клавиатуру для оповещений с опциями управления запросами."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❓ Как это работает?", callback_data="faq"))
    markup.add(InlineKeyboardButton("📑 Активные запросы", callback_data="my_requests"))
    markup.insert(InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert"))
    return markup


def type_alert() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора типа оповещений."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔍 Поиск слотов", callback_data="default_alert"))
    markup.add(InlineKeyboardButton("⭐️ Премиум поиск", callback_data="premium_alert"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))
    return markup


async def get_warehouses_markup(redis_client):
    """Асинхронно создает клавиатуру со списком складов."""
    markup = InlineKeyboardMarkup()
    try:
        warehouses = await redis_client.get_warehouses()
        for warehouse in warehouses:
            markup.add(InlineKeyboardButton(
                text=warehouse['name'],
                callback_data=f"warehouse_{warehouse['id']}"
            ))
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры складов: {e}")
        return None
    return markup


async def warehouse_markup(redis_client, selected_warehouses=None, page=0) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора складов с поддержкой пагинации."""
    selected_warehouses = [str(id) for id in (selected_warehouses or [])]
    warehouses = await redis_client.get_warehouses()

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

        if len(callback_data) <= 64:
            markup.insert(InlineKeyboardButton(text, callback_data=callback_data))

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_back_{page-1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_forward_{page+1}"))

    if navigation_buttons:
        markup.row(*navigation_buttons)

    if selected_warehouses:
        markup.row(
            InlineKeyboardButton("Продолжить ▶️", callback_data="continue"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        )
    else:
        markup.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        )

    return markup


async def update_markup(message: types.Message, markup: InlineKeyboardMarkup):
    """Обновляет сообщение с новой клавиатурой или отправляет новое сообщение при ошибке."""
    try:
        await message.edit_reply_markup(reply_markup=markup)
    except MessageNotModified:
        await message.delete()
        await message.answer("Обновлено:", reply_markup=markup)
    except Exception:
        return None


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
        markup.row(
            InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        )
    else:
        # Если нет выбранных типов поставок, просто добавляем кнопку "Отмена"
        markup.insert(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return markup


def acceptance_coefficient_markup():
    """Создает клавиатуру для выбора коэффициента приемки."""
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
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return markup


def period_selection_markup():
    """Создает клавиатуру для выбора периода уведомления."""
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
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return markup


def go_booking() -> InlineKeyboardMarkup:
    """Создает клавиатуру для запуска бота."""
    markup = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(
            text="🚀 Перейти к бронированию",
            url="https://seller.wildberries.ru/supplies-management/all-supplies"
        )
    ]
    markup.add(*buttons)
    return markup


def requests_keyboard(user_requests):
    markup = InlineKeyboardMarkup()
    for i, request in enumerate(user_requests, start=1):
        warehouse_name = request.get('warehouse_name', 'Неизвестный склад')
        date = request.get('date', 'Неизвестная дата')
        button_text = f"{i}. {warehouse_name} | {date}"
        callback_data = f"request_details_{i}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_my_requests"))
    return markup


def back_btn(date) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⛔️ Завершить поиск", callback_data=f"stop_search_{date}"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_requst"))
    return markup


def back_btn2() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_requst"))
    return markup


def back_btn3() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))
    return markup