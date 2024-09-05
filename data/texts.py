START_TEXT = "CAACAgIAAxkBAAEMxFlm2kCqKQ1gSucq6ye0v7_kaPNxAQACkwADEC-SNfxEinlBd590NgQ"
MAIN_MENU_TEXT = "<b>💠 Главное меню</b>"
ALERTS_TEXT = ("<b>💠 Главное меню</b>\n\n"
               "<i>Получайте первыми уведомления о бесплатных слотах на складах Wildberries</i>\n")
CREATE_ALERT_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                     "<i>Выберите тип оповощения:</i>")
SELECT_WAREHOUSE_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                         "<i>Выберите склады (можно несколько):</i>")
SELECT_SUPPLY_TYPES_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                            "<i>Выберите типы поставок (можно несколько):</i>")
SELECT_COEFFICIENT_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                           "<i>Выберите коэффициент приемки (например если выбрать 1, то система будет искать коэффициенты 1 и меньше):</i>")
SELECT_PERIOD_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                     "<i>Выберите период поиска:</i>")
SELECT_ALERT_TEXT = ("<b>➕ Создание запроса:</b>\n\n"
                     "<i>Сколько раз вас уведомить? (Например если выбрать до первого уведомления, то система пришлёт первый подходящий под ваши параметры слот и всё)</i>")

FAQ_TEXT = "<b>Здесь будет инструкция..</b>"

TECH_SUPPORT_TEXT = "👨‍💻 <b>Напишите свое обращение в поддержку бота.\n\nМы всегда рассматриваем все сообщения!</b>"


FINAL_NOTIFICATION_TEXT = (
    "✅ <b>Ваши параметры поиска:</b>\n\n"
    "🏨 <b>Склад:</b> {warehouse_names}\n"
    "📦 <b>Вид приемки:</b> {supply_types_names}\n"
    "📊 <b>Максимальный тариф:</b> {coefficient}\n"
    "🗓 <b>Дата отгрузки:</b> Ближайшие {period}"
)


SUPPLY_TYPE_RUS_MAP = {
    "mono_pallets": "Монопаллеты",
    "boxes": "Короба",
    "super_safe": "Суперсейф",
    "qr_supply": "QR-поставка"
}

SUPPLY_NUM_MAP = {
    "mono_pallets": "5",
    "boxes": "2",
    "super_safe": "6",
    "qr_supply": "0"
}

PERIOD_MAP = {
    "today": "Сегодня",
    "tomorrow": "Завтра",
    "3days": "3 дня",
    "week": "Неделя",
    "month": "Месяц"
}