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

FAQ_TEXT = ("<b>❓ Как это работает:</b>\n\n"
            "<b>Принцип работы бота.</b>\n\n"
            "<i>- Бот идет на ВБ и спрашивает слоты\n"
            "- ВБ отдает список слотов в том состоянии, в котором они есть в текущую секунду\n"
            "- Бот проходит по всем слотам, смотрит кто на что подписан и рассылает вам в личку</i>\n\n"
            "<b>Проблемы:</b>\n\n"
            "<b>В: Бот не прислал склад, который был пойман в ручном режиме.</b>\n"
            "<i>О:\n"
            "- Бот пошел на ВБ в 09:00:00 и забрал слоты, которые отдал ВБ\n"
            "- Бот разослал вам слоты и пошел ждать минуту\n"
            "- В 09:00:10 на ВБ появился слот на какой-то склад\n"
            "- В 09:00:50 этот слот пропал с ВБ\n"
            "- В 09:01:00 бот пошел на ВБ за слотами. Само собой ВБ не скажет ему о слоте, которого уже нет</i>\n\n"
            "<b>В: Бот не присылает слоты.</b>\n"
            "<i>О: 1. Либо слоты не настроены/настроены неверно - для этого надо отправить команду «Активные склады» и убедиться, что в ответе от бота есть все нужные вам склады, даты и коэффициента настроены корректно.</i>\n"
            "2. Либо слотов просто нет. Поэтому бот молчит.\n\n"
            "<b>В: В другом боте прислали, а в этом нет.</b>"
            "<i>О: Потому что это совпадение. Так же бывает, что в нашем боте есть слот, которого нет в другом боте. Детальное объяснение работы бота смотри в первом вопросе.</i>\n\n"
            "<b>В: Как удалить склады, которые мне не нужны?</b>\n"
            "<i>О: Кнопка Активные запросы - выбрать запрос - ⛔️ Завершить поиск</i>\n\n"
            "<b>В: Почему бот показывает один коэф, а не деле другой?</b>\n"
            "<i>О: Потому что кроме вас еще 180 тысяч селлеров ищет этот слот. Многие бронируют с помощью автоброни.</i>\n\n"
            "<b>В: Почему бот шлет одни и те же данные много раз?</b>\n"
            "<i>О: Вы используете бота, чтобы узнать о слотах, которые появляются не часто."
            "Когда бот находит слот, его основная задача - долбить сообщениями, пока вы не сделаете поставку и не отпишетесь от этого склада. "
            "Если бот будет присылать сообщение только один раз, вы не будете знать, живой ещё слот или нет. "
            "А информация должна быть актуальной</i>")


SUBSCRIBE_TEXT = ("<b>⭐️ Оформление подписки</b>\n\n"
                  "<i>Стоимость подписки на 1 месяц - 237 ₽</i>")


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
}

SUPPLY_NUM_MAP = {
    "mono_pallets": "5",
    "boxes": "2",
    "super_safe": "6",
}

PERIOD_MAP = {
    "today": "Сегодня",
    "tomorrow": "Завтра",
    "3days": "3 дня",
    "week": "Неделя",
    "month": "Месяц"
}