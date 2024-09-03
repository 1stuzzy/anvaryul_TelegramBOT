import asyncio
import html
from loguru import logger


class NotificationService:
    def __init__(self, api_client, redis_client, bot, max_concurrent_requests=5, min_delay_between_requests=2.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests
        logger.debug("NotificationService инициализирован")

    async def check_and_notify_users(self):
        await self.redis_client.init()
        logger.debug("Redis клиент инициализирован")

        while True:
            try:
                logger.debug("Запуск цикла проверки и уведомлений")
                user_requests = await self.redis_client.get_user_requests()
                logger.debug(f"Получено {len(user_requests)} запросов пользователей из Redis")

                tasks = [self.process_user_request(request) for request in user_requests]
                await asyncio.gather(*tasks)
                logger.debug("Все запросы обработаны")

                await asyncio.sleep(60)
                logger.debug("Цикл проверки завершен, ожидание 60 секунд")
            except Exception as e:
                logger.error(f"Ошибка при проверке и уведомлении: {e}")
                await asyncio.sleep(60)
                logger.debug("Перезапуск цикла проверки через 60 секунд после ошибки")

    async def process_user_request(self, request):
        try:
            logger.debug(f"Обработка запроса пользователя с параметрами: {request}")

            required_keys = ['user_id', 'warehouse_ids', 'coefficient', 'supply_types', 'status']
            for key in required_keys:
                if key not in request:
                    logger.error(f"Запрос пользователя не содержит ключ '{key}': {request}")
                    return

            async with self.semaphore:
                await asyncio.sleep(self.min_delay_between_requests)
                logger.debug(f"Задержка между запросами: {self.min_delay_between_requests} секунд")

                coefficients = await self.api_client.get_coefficients(
                    warehouse_ids=request['warehouse_ids'].split(',')
                )
                logger.debug(f"Получены коэффициенты: {coefficients}")

                relevant_changes = []
                for coef in coefficients:
                    coef_value = coef['coefficient']
                    user_coef = request['coefficient']

                    # Проверка, является ли коэффициент в диапазоне
                    if isinstance(user_coef, str) and user_coef.startswith("<"):
                        threshold = float(user_coef[1:])
                        if coef_value < threshold:
                            relevant_changes.append(coef)
                    else:
                        if coef_value == float(user_coef):
                            relevant_changes.append(coef)

                logger.debug(f"Найдено {len(relevant_changes)} подходящих изменений для пользователя {request['user_id']}")

                if relevant_changes:
                    messages = [
                        f"📦 <b>Обновление по складу {html.escape(str(change['warehouseName']))}</b>\n"
                        f"Тип поставки: {html.escape(str(change['boxTypeName']))}\n"
                        f"Дата: {html.escape(str(change['date']))}\n"
                        f"Коэффициент приёмки: {html.escape(str(change['coefficient']))}\n"
                        for change in relevant_changes
                    ]

                    final_message = "\n".join(messages)
                    logger.debug(f"Сформировано сообщение для пользователя {request['user_id']}: {final_message}")

                    last_message_key = f"last_message:{request['user_id']}"
                    last_message = await self.redis_client.redis.get(last_message_key)

                    # Проверка на повторное сообщение
                    if last_message != final_message:
                        await self.notify_user(request['user_id'], final_message)
                        await self.redis_client.redis.set(last_message_key, final_message)
                        logger.debug(f"Сообщение отправлено и сохранено для пользователя {request['user_id']}")

                        # Если статус 0 (до первого уведомления), нужно остановить дальнейшие уведомления
                        if request['status'] == 0:
                            logger.debug(f"Остановить дальнейшие уведомления для пользователя {request['user_id']} после первого отправленного сообщения.")
                            return

                    else:
                        logger.debug(f"Сообщение не отправлено, так как оно идентично предыдущему для пользователя {request['user_id']}")
                else:
                    logger.debug(f"Для пользователя {request['user_id']} нет подходящих изменений")
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса пользователя: {e}")

    async def notify_user(self, user_id: int, message: str):
        try:
            logger.debug(f"Отправка уведомления пользователю {user_id}")

            # Экранирование специальных символов в сообщении
            message = html.escape(message)

            # Разбиваем сообщение на части, если оно длиннее 4096 символов
            max_length = 4096
            messages = [message[i:i + max_length] for i in range(0, len(message), max_length)]

            for msg in messages:
                await self.bot.send_message(user_id, msg)

            logger.debug(f"Уведомление отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")