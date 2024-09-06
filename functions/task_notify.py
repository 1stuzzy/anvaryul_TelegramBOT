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

    async def check_and_notify_users(self):
        await self.redis_client.init()
        delay = 5
        while True:
            try:
                user_requests = await self.redis_client.get_user_requests()

                tasks = [self.process_user_request(request) for request in user_requests]
                await asyncio.gather(*tasks)
                logger.debug("Все запросы обработаны")

                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Ошибка при проверке и уведомлении: {e}")
                await asyncio.sleep(delay)

    async def notify_user(self, user_id: int, message: str, delay: float = 5.0):
        try:
            await asyncio.sleep(delay)
            markup = go_booking()
            try:
                # Пытаемся отправить новое сообщение
                await self.bot.send_message(user_id, message, reply_markup=markup, parse_mode='HTML')
                logger.debug(f"Уведомление отправлено пользователю {user_id}")
            except Exception as e:
                # Если возникает ошибка, связанная с тем, что сообщение не изменилось
                if "Message is not modified" in str(e):
                    logger.warning(f"Попытка отправить сообщение пользователю {user_id} не удалась: {e}")
                else:
                    raise e
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
            pass


    async def process_user_request(self, request):
        try:
            # Убедитесь, что отсутствующие ключи получают значения по умолчанию
            notify = request.get('notify', '0')  # по умолчанию '0', если нет значения
            status_request = request.get('status_request', 'false').lower() == 'true'
            if not status_request:
                logger.info(f"Запрос пользователя {request.get('user_id')} с временной меткой {request.get('date')} отключен, обработка остановлена.")
                return

            required_keys = ['user_id', 'warehouse_ids', 'coefficient', 'supply_types']
            missing_keys = [key for key in required_keys if key not in request]
            if missing_keys:
                logger.warning(f"Пропущены ключи {missing_keys} в запросе пользователя {request.get('user_id')}")
                return

            try:
                user_id = int(request['user_id']) if request.get('user_id') is not None else 0
                coefficient = float(request['coefficient']) if request.get('coefficient') is not None else 0.0
                notify = int(notify) if notify is not None else 0
                warehouse_ids = request['warehouse_ids'].split(',')
                supply_types = request['supply_types'].split(',')
                status_request = status_request == 'true'
                logger.debug(f"Processing request for user_id: {request.get('user_id')}, coefficient: {request.get('coefficient')}, notify: {notify}")
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка в данных запроса пользователя {request.get('user_id')}: {e}")
                return


            if not status_request:
                logger.info(f"Запрос пользователя {request.get('user_id')} с временной меткой {request.get('date')} отключен, обработка остановлена.")
                return

            async with self.semaphore:
                await asyncio.sleep(self.min_delay_between_requests)

                max_attempts = len(self.tokens) * 3
                attempt = 0
                delay = 10
                unauthorized_attempts = 0

                while attempt < max_attempts:
                    try:
                        coefficients = await self.api_client.get_coefficients(warehouse_ids=warehouse_ids)
                        if not coefficients:
                            logger.info(f"Коэффициенты не получены для запроса пользователя {user_id}")
                            return
                        break
                    except Exception as e:
                        error_message = str(e)
                        if "429" in error_message:
                            attempt += 1
                            if attempt < max_attempts:
                                await asyncio.sleep(delay)
                                self.switch_token()
                                delay *= 2
                            else:
                                logger.error(f"Превышено максимальное количество попыток для запроса пользователя {user_id}")
                                return
                        elif "401 Unauthorized" in error_message:
                            logger.warning("Ошибка авторизации. Переключение токена.")
                            self.api_client.switch_token()
                            unauthorized_attempts += 1
                            if unauthorized_attempts >= len(self.api_client.tokens):
                                logger.error("Все токены не прошли авторизацию. Остановка попыток.")
                                return
                        else:
                            logger.error(f"Ошибка при получении коэффициентов: {e}")
                            return

                filtered_coefficients = [
                    coef for coef in coefficients
                    if coef.get('warehouseID') is not None and int(coef.get('warehouseID')) in map(int, warehouse_ids)
                    and coef.get('boxTypeID') is not None and int(coef.get('boxTypeID')) in map(int, request['boxTypeID'].split(','))
                ]


                if not filtered_coefficients:
                    logger.info(f"Фильтрованные коэффициенты отсутствуют для запроса пользователя {user_id}")
                    return

                for coef in filtered_coefficients:
                    coef_value = coef.get('coefficient')
                    box_type_id = coef.get('boxTypeID')
                    date = datetime.strptime(coef.get('date'), '%Y-%m-%dT%H:%M:%SZ').strftime('%d.%m.%Y')

                    relevant_change = False

                    if request['coefficient'].startswith("<"):
                        threshold = float(request['coefficient'][1:])
                        if coef_value >= 0 and coef_value < threshold:
                            relevant_change = True
                            coefficient_display = f"<{coef_value}"
                    else:
                        threshold = float(request['coefficient'])
                        if coef_value >= 0 and coef_value <= threshold:
                            relevant_change = True
                            coefficient_display = str(coef_value)

                    if relevant_change:
                        message_key = f"sent:{user_id}:{coef['warehouseID']}:{box_type_id}:{coef['date']}:{coef_value}"
                        already_sent = await self.redis_client.redis.exists(message_key)

                        if not already_sent:
                            message = (
                                f"<b>🎉 Слот найден:</b>\n\n"
                                f"<i><b>Дата:</b> {date}</i>\n"
                                f"<i><b>Склад:</b> {coef['warehouseName']}</i>\n"
                                f"<i><b>Тип поставки:</b> {coef['boxTypeName']}</i>\n"
                                f"<i><b>Коэффициент:</b> {coefficient_display}</i>\n"
                            )

                            await self.notify_user(user_id, message)
                            await self.redis_client.redis.set(message_key, "sent", ex=24 * 60 * 60)

                            if notify == 0:
                                logger.info(f"Запрос пользователя {user_id} завершен после первого уведомления.")
                                return

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса пользователя {user_id}: {e}")


    async def stop_user_task(user_id: int, task_id: str):
        try:
            # Останавливаем задачу
            result = current_app.control.revoke(task_id, terminate=True)
            
            if result:
                logger.info(f"Задача {task_id} для пользователя {user_id} успешно остановлена.")
                # Обновляем статус задачи в Redis или другой БД
                await self.redis.hset(f"user_task:{user_id}:{task_id}", 'status', 'stopped')
                return True
            else:
                logger.error(f"Не удалось остановить задачу {task_id} для пользователя {user_id}.")
                return False

        except Exception as e:
            logger.error(f"Ошибка при остановке задачи {task_id} для пользователя {user_id}: {e}")
            return False

