from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified
from aiogram import types
from loguru import logger
from data import texts

def main_keyboard():
    """Создает основную клавиатуру с кнопкой оповещений."""
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("💠 Главное меню"),
        KeyboardButton("👨‍💻 Техническая поддержка")
    )


def menu_keyboard():
    """Создает клавиатуру меню с кнопками оповещений и FAQ."""
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("❓ Как это работает?", callback_data="faq"),
        InlineKeyboardButton("⭐️ Оформить подписку", callback_data="subscribe"),
        InlineKeyboardButton("📑 Активные запросы", callback_data="my_requests"),
        InlineKeyboardButton("➕ Создать запрос", callback_data="create_alert")
    )


def support_keyboard(support):
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("📩 Написать сообщение", url=f"t.me/{support}")
    )


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
        return InlineKeyboardMarkup().row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    markup = InlineKeyboardMarkup(row_width=2)
    for warehouse in warehouses:
        is_selected = str(warehouse["id"]) in selected_warehouses
        text = f"✅ {warehouse['name']}" if is_selected else warehouse['name']
        callback_data = f"{'unselect' if is_selected else 'select'}_{warehouse['id']}"

        markup.insert(InlineKeyboardButton(text, callback_data=callback_data))

    if selected_warehouses:
        markup.row(
            InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply"),
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
        await message.answer(texts.select_warehouse_text, reply_markup=markup)
    except Exception as e:
        logger.error(f"Ошибка при обновлении клавиатуры: {e}")


def supply_types_markup(selected_supply_types=None):
    """Создает клавиатуру для выбора типов поставок."""
    selected_supply_types = set(selected_supply_types or [])
    markup = InlineKeyboardMarkup(row_width=2)

    for name, value in texts.types_map.items():
        bt_text = f"✅ {name}" if value in selected_supply_types else name
        callback_data = f"{'unselecttype' if value in selected_supply_types else 'selecttype'}_{value}"
        markup.insert(InlineKeyboardButton(text=bt_text, callback_data=callback_data))

    if selected_supply_types:
        markup.row(
            InlineKeyboardButton("Продолжить ▶️", callback_data="continue_supply_coeff"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        )
    else:
        markup.insert(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return markup



def acceptance_coefficient_markup():
    """Создает клавиатуру для выбора коэффициента приемки."""
    buttons = [
        InlineKeyboardButton(text=f"<{i}", callback_data=f"coefficient_{i}") for i in range(1, 9)
    ]
    buttons.insert(0, InlineKeyboardButton(text="0", callback_data="coefficient_0"))

    markup = InlineKeyboardMarkup(row_width=4)
    markup.add(*buttons[:4])
    markup.add(*buttons[4:])
    markup.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return markup


def period_selection_markup():
    """Создает клавиатуру для выбора периода уведомления."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(*(InlineKeyboardButton(text=p[0], callback_data=f"period_{p[1]}") for p in texts.period_map))
    markup.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return markup


def notification_count_markup() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора количества уведомлений."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="До первого уведомления", callback_data="notify_once"),
        InlineKeyboardButton(text="Без ограничений", callback_data="notify_unlimited"),
    )
    markup.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return markup


def go_booking() -> InlineKeyboardMarkup:
    """Создает клавиатуру для запуска бота."""
    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(
            text="🚀 Перейти к бронированию",
            url="https://seller.wildberries.ru/supplies-management/all-supplies"
        )
    )


def requests_keyboard(user_requests):
    markup = InlineKeyboardMarkup()
    for i, request in enumerate(user_requests, start=1):
        warehouse_name = request.get('warehouse_name', 'Неизвестный склад')
        date = request.get('date', 'Неизвестная дата')

        status_symbol = "🟢" if request.get('status_request', 'False').lower() == 'true' else "🔴"
        button_text = f"{status_symbol} {i}. {warehouse_name} | {date}"
        markup.add(InlineKeyboardButton(button_text, callback_data=f"request_details_{i}"))

    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_my_requests"))
    return markup


def back_btn(date, status_request) -> InlineKeyboardMarkup:
    """Создает кнопку для завершения поиска или возврата назад."""
    markup = InlineKeyboardMarkup()
    if status_request.lower() == 'true':
        markup.add(InlineKeyboardButton("⛔️ Завершить поиск", callback_data=f"stop_search_{date}"))
    markup.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_request"))
    return markup


def subscribe_kb() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подписки."""
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("Перейти к оформлению", callback_data="go_to_subscribe"),
        InlineKeyboardButton("↩️ Назад", callback_data="back_menu")
    )


def subscription_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="1 день", callback_data="subscribe_1"),
        InlineKeyboardButton(text="3 дня", callback_data="subscribe_3"),
        InlineKeyboardButton(text="7 дней", callback_data="subscribe_7"),
        InlineKeyboardButton(text="30 дней", callback_data="subscribe_30")
    )
    return keyboard


def payment_btn(pay_link, pay_id, sub_days):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="Перейти к оплате", url=f"{pay_link}")
    )
    keyboard.add(
        InlineKeyboardButton(text="Проверить платеж", callback_data=f"checkpay_{pay_id}_{sub_days}"),
    )
    return keyboard