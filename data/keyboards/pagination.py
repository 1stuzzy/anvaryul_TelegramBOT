from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_pagination_keyboard(warehouses, page: int, selected_warehouses=None, page_size: int = 10):
    if selected_warehouses is None:
        selected_warehouses = []

    keyboard = InlineKeyboardMarkup(row_width=1)
    start_index = page * page_size
    end_index = start_index + page_size
    paginated_warehouses = warehouses[start_index:end_index]

    for wh in paginated_warehouses:
        warehouse_id = str(wh.get('ID'))
        selected = " ✅" if warehouse_id in selected_warehouses else ""
        button = InlineKeyboardButton(
            text=wh.get('name', 'Неизвестный склад') + selected,
            callback_data=f"select_{warehouse_id}_{page}"
        )
        keyboard.add(button)

    total_pages = (len(warehouses) - 1) // page_size + 1
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("◀️", callback_data=f"page_{page - 1}"))
    pagination_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("▶️", callback_data=f"page_{page + 1}"))

    keyboard.row(*pagination_buttons)

    if selected_warehouses:
        keyboard.add(InlineKeyboardButton("Продолжить", callback_data=f"continue_{page}"))

    return keyboard

