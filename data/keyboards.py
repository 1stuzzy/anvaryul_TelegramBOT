from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified
from aiogram import types
from loader import config
from data import texts


def subscription_required(chat_link: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой для перехода в чат сообщества."""
    markup = InlineKeyboardMarkup()
    join_chat_button = InlineKeyboardButton(text="🔗 Перейти в чат", url=chat_link)
    markup.add(join_chat_button)
    return markup


def main_keyboard():
    """Создает основную клавиатуру с кнопкой оповещений."""
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("💠 Главное меню"),
        KeyboardButton("👨‍💻 Техническая поддержка")
    )


def menu_keyboard():
    """Создает клавиатуру меню с кнопками оповещений и FAQ."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💠 Личный кабинет", callback_data="personal_area"))
    markup.add(
        InlineKeyboardButton("❓ Как это работает?", callback_data="faq"),
        InlineKeyboardButton("⭐️ Оформить подписку", callback_data="subscribe"),
        InlineKeyboardButton("📑 Активные запросы", callback_data="my_requests"),
        InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert")
    )
    return markup


def alerts_keyboard():
    """Создает клавиатуру для оповещений с опциями управления запросами."""
    return menu_keyboard()


def back_to_alerts_kb():
    """Создает клавиатуру для возврата к оповещениям."""
    return menu_keyboard()


def type_alert():
    """Создает клавиатуру для выбора типа оповещений."""
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔍 Поиск слотов", callback_data="default_alert"),
        InlineKeyboardButton("↩️ Назад", callback_data="back_menu")
    )


async def get_warehouses_markup(redis_client):
    """Асинхронно создает клавиатуру со списком складов."""
    markup = InlineKeyboardMarkup()
    warehouses = await redis_client.get_warehouses_list()
    for warehouse in warehouses:
        markup.add(InlineKeyboardButton(
            text=warehouse['name'],
            callback_data=f"warehouse_{warehouse['id']}"
        ))
    return markup


async def warehouse_markup(redis_client, selected_warehouses=None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора складов без поддержки пагинации."""
    selected_warehouses = [str(id) for id in (selected_warehouses or [])]
    warehouses = await redis_client.get_warehouses_list()

    if not warehouses:
        return InlineKeyboardMarkup().row(InlineKeyboardButton(text="❌ Отмена", callback_data="close_callback"))

    markup = InlineKeyboardMarkup(row_width=2)
    for warehouse in warehouses:
        is_selected = str(warehouse["id"]) in selected_warehouses
        text = f"✅ {warehouse['name']}" if is_selected else warehouse['name']
        callback_data = f"{'unselect' if is_selected else 'select'}_{warehouse['id']}"

        markup.insert(InlineKeyboardButton(text, callback_data=callback_data))

    if selected_warehouses:
        markup.row(
            InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply"),
        )
        markup.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="close_callback")
        )
    else:
        markup.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="close_callback")
        )

    return markup


async def update_markup(message: types.Message, markup: InlineKeyboardMarkup):
    """Обновляет сообщение с новой клавиатурой или отправляет новое сообщение при ошибке."""
    try:
        await message.edit_reply_markup(reply_markup=markup)
    except MessageNotModified:
        await message.delete()
        await message.answer(texts.select_warehouse_text, reply_markup=markup)
    except Exception:
        return


def supply_types_markup(selected_supply_types=None):
    """Создает клавиатуру для выбора типов поставок."""
    selected_supply_types = set(selected_supply_types or [])
    markup = InlineKeyboardMarkup(row_width=2)
    for name, (value, type_id) in texts.types_map.items():
        bt_text = f"✅ {name}" if type_id in selected_supply_types else name
        callback_data = f"{'unselecttype' if type_id in selected_supply_types else 'selecttype'}_{type_id}"
        markup.insert(InlineKeyboardButton(text=bt_text, callback_data=callback_data))

    if selected_supply_types:
        markup.row(InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply_coeff"))

    markup.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_callback"))

    return markup


def acceptance_coefficient_markup():
    """Создает клавиатуру для выбора коэффициента приемки."""
    buttons = [
        InlineKeyboardButton(text=f"<{i}", callback_data=f"coefficient_{i}") for i in range(1, 8)
    ]
    buttons.insert(0, InlineKeyboardButton(text="0", callback_data="coefficient_0"))

    markup = InlineKeyboardMarkup(row_width=4)

    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i + 4])

    markup.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_callback"))
    return markup


def period_selection_markup():
    """Создает клавиатуру для выбора периода уведомления."""
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(*(InlineKeyboardButton(text=p[0], callback_data=f"period_{key}") for key, p in texts.period_map.items()))

    markup.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_callback"))
    return markup


def notification_count_markup() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора количества уведомлений."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="До первого уведомления", callback_data="notify_once"),
        InlineKeyboardButton(text="Без ограничений", callback_data="notify_unlimited"),
    )
    markup.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_callback"))
    return markup


def go_booking() -> InlineKeyboardMarkup:
    """Создает клавиатуру для запуска бота."""
    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(
            text="🚀 Перейти к бронированию",
            url="https://seller.wildberries.ru/supplies-management/all-supplies"
        )
    )


async def requests_keyboard(user_requests, redis_client):
    markup = InlineKeyboardMarkup()
    for i, request in enumerate(user_requests, start=1):
        warehouse_id = request.get('warehouse_ids')
        warehouse_id_list = warehouse_id.split(',') if warehouse_id else []

        warehouse_names = [await redis_client.get_warehouse_name(wh_id) for wh_id in warehouse_id_list]
        warehouse_name = ', '.join(warehouse_names)

        date = request.get('start_date')

        status_symbol = "🟢" if request.get('status_request', 'False').lower() == 'true' else "🔴"
        button_text = f"{status_symbol} {i}. {warehouse_name} | {date}"
        markup.add(InlineKeyboardButton(button_text, callback_data=f"request_details_{i}"))

    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))
    return markup


def back_btn(request_id, status_request) -> InlineKeyboardMarkup:
    """Создает кнопку для завершения поиска или возврата назад."""
    markup = InlineKeyboardMarkup()
    if status_request.lower() == 'true':
        markup.add(InlineKeyboardButton("⛔️ Завершить поиск", callback_data=f"stop_search_{request_id}"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_request"))
    return markup


def subscribe_kb() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подписки."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Перейти к оформлению", callback_data="go_to_subscribe"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_menu"))

    return markup


def subscription_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="1 месяц", callback_data="subscribe_30"),
        InlineKeyboardButton(text="2 месяца", callback_data="subscribe_60"),
        InlineKeyboardButton(text="3 месяца", callback_data="subscribe_90"),
        InlineKeyboardButton(text="1 год", callback_data="subscribe_365"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="close_callback")
    )
    return keyboard


def payment_btn(pay_link, pay_id, sub_days):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="Перейти к оплате", url=f"{pay_link}")
    )
    keyboard.add(
        InlineKeyboardButton(text="Я оплатил", callback_data=f"checkpay_{pay_id}_{sub_days}"),
    )
    return keyboard


def close_btn():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_callback"))
    return keyboard


def back():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_menu"))
    return keyboard