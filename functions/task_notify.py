import asyncio
from loguru import logger
from data.keyboards.main_kbs import go_booking
from datetime import datetime


class NotificationService:
    def __init__(self, api_client, redis_client, bot, tokens, max_concurrent_requests=10, min_delay_between_requests=1.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.tokens = tokens  # Список токенов
        self.current_token_index = 0  # Индекс текущего токена
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests

    def get_current_token(self):
        return self.tokens[self.current_token_index]

    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        logger.warning(f"Переключение на следующий токен: {self.get_current_token()}")

    async def check_and_notify_users(self):
        await self.redis_client.init()
        delay = 5
        while True:
            try:
                logger.debug("Запуск цикла проверки и уведомлений")
                user_requests = await self.redis_client.get_user_requests()
                logger.debug(f"Получено {len(user_requests)} запросов пользователей из Redis")

                tasks = [self.process_user_request(request) for request in user_requests]
                await asyncio.gather(*tasks)
                logger.debug("Все запросы обработаны")

                await asyncio.sleep(delay)
                logger.debug(f"Цикл проверки завершен, ожидание {delay} секунд")
            except Exception as e:
                logger.error(f"Ошибка при проверке и уведомлении: {e}")
                await asyncio.sleep(delay)
                logger.debug(f"Перезапуск цикла проверки через {delay} секунд после ошибки")

    async def notify_user(self, user_id: int, message: str, delay: float = 5.0):
        try:
            await asyncio.sleep(delay)
            logger.debug(f"Отправка уведомления пользователю {user_id}")
            markup = go_booking()
            await self.bot.send_message(user_id, message, reply_markup=markup, parse_mode='HTML')
            logger.debug(f"Уведомление отправлено пользователю {user_id}")

            logger.debug(f"Задержка перед следующей отправкой уведомления: {delay} секунд")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
            pass

    async def process_user_request(self, request):
        try:
            logger.debug(f"Обработка запроса пользователя с параметрами: {request}")

            required_keys = ['user_id', 'warehouse_ids', 'coefficient', 'supply_types', 'notify']
            for key in required_keys:
                if key not in request:
                    logger.error(f"Запрос пользователя не содержит ключ '{key}': {request}")
                    return

            async with self.semaphore:
                await asyncio.sleep(self.min_delay_between_requests)
                logger.debug(f"Задержка между запросами: {self.min_delay_between_requests} секунд")

                max_attempts = len(self.tokens) * 3
                attempt = 0
                delay = 10
                unauthorized_attempts = 0

                while attempt < max_attempts:
                    try:
                        current_token = self.get_current_token()
                        logger.debug(f"Попытка {attempt + 1} с токеном: {current_token}")

                        coefficients = await self.api_client.get_coefficients(
                            warehouse_ids=request['warehouse_ids'].split(',')
                        )

                        if not coefficients:
                            logger.error(f"Не удалось получить коэффициенты для запросов: {request}")
                            return

                        logger.debug(f"Получены коэффициенты: {coefficients}")
                        break

                    except Exception as e:
                        error_message = str(e)
                        logger.error(f"Ошибка при получении коэффициентов: {error_message}")

                        if "429" in error_message:
                            attempt += 1
                            if attempt < max_attempts:
                                logger.warning(f"Превышен лимит запросов, попытка {attempt} из {max_attempts}. Переключение токена.")
                                await asyncio.sleep(delay)
                                self.switch_token()
                                delay *= 2
                            else:
                                logger.error("Достигнуто максимальное количество попыток. Запрос будет отменен.")
                                return
                        elif "401 Unauthorized" in error_message:
                            logger.warning("Ошибка авторизации. Переключение токена.")
                            self.api_client.switch_token()
                            unauthorized_attempts += 1
                            if unauthorized_attempts >= len(self.api_client.tokens):
                                logger.error("Все токены не прошли авторизацию. Остановка попыток.")
                                break  # Остановка цикла, если все токены не авторизованы
                        else:
                            unauthorized_attempts = 0

                if attempt == max_attempts:
                    logger.error("Не удалось получить коэффициенты после максимального количества попыток.")
                    return

                # Фильтрация коэффициентов по складам и типам поставок, заданным пользователем
                filtered_coefficients = [
                    coef for coef in coefficients
                    if coef.get('warehouseID') in map(int, request['warehouse_ids'].split(',')) and
                       coef.get('boxTypeID') in [int(bt) for bt in request['boxTypeID'].split(',')]
                ]

                for coef in filtered_coefficients:
                    coef_value = coef.get('coefficient')
                    user_coef = request['coefficient']
                    box_type_id = coef.get('boxTypeID')
                    date = datetime.strptime(coef.get('date'), '%Y-%m-%dT%H:%M:%SZ').strftime('%d.%m.%Y %H:%M')

                    relevant_change = False
                    if user_coef.startswith("<"):
                        threshold = float(user_coef[1:])
                        if coef_value >= 0 and coef_value < threshold:
                            relevant_change = True
                    else:
                        threshold = float(user_coef)
                        if coef_value >= 0 and coef_value <= threshold:
                            relevant_change = True

                    if relevant_change:
                        message_key = f"sent:{request['user_id']}:{coef['warehouseID']}:{box_type_id}:{coef['date']}:{coef_value}"
                        already_sent = await self.redis_client.redis.exists(message_key)

                        if not already_sent:
                            message = (
                                f"<b>🎉 Слот найден:</b>\n\n"
                                f"<i><b>Дата:</b> {date}</i>\n"
                                f"<i><b>Склад:</b> {coef['warehouseName']}</i>\n"
                                f"<i><b>Тип поставки:</b> {coef['boxTypeName']}</i>\n"
                                f"<i><b>Коэффициент:</b> {coef_value}</i>\n"
                            )

                            await self.notify_user(request['user_id'], message)
                            await self.redis_client.redis.set(message_key, "sent", ex=24 * 60 * 60)
                            logger.debug(f"Сообщение отправлено и сохранено для пользователя {request['user_id']} по ключу {message_key}")

                            if request['notify'] == 0:
                                logger.debug(f"Остановить дальнейшие уведомления для пользователя {request['user_id']} после первого отправленного сообщения.")
                                return
                        else:
                            logger.debug(f"Сообщение уже было отправлено для ключа {message_key}, повторная отправка отменена")

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса пользователя: {e}")




