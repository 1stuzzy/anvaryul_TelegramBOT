import asyncio
from loguru import logger
from aiogram import Bot
from datetime import datetime
from data.keyboards.main_kbs import go_booking
from db.redis_base import RedisClient
from functions.wb_api import ApiClient


class NotificationService:
    def __init__(self, api_client: ApiClient, redis_client: RedisClient, bot: Bot, max_concurrent_requests=10, min_delay_between_requests=1.1):
        self.api_client = api_client
        self.redis_client = redis_client
        self.bot = bot
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.min_delay_between_requests = min_delay_between_requests
        self.tasks = {}

    async def check_and_notify_users(self):
        logger.info("Starting check_and_notify_users task")
        await self.redis_client.init()
        delay = 5
        while True:
            try:
                user_requests = await self.redis_client.get_user_requests()
                logger.debug(f"Received {len(user_requests)} user requests")

                tasks = [self.process_user_request(request) for request in user_requests]
                if tasks:
                    await asyncio.gather(*tasks)
                    logger.debug("All requests processed")
                else:
                    logger.debug("No tasks to process")

                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Error in check_and_notify_users: {e}")
                await asyncio.sleep(delay)

    async def notify_user(self, user_id: int, message: str, delay: float = 5.0):
        try:
            logger.debug(f"Attempting to send notification to user {user_id} in {delay} seconds")
            await asyncio.sleep(delay)
            markup = go_booking()
            try:
                await self.bot.send_message(user_id, message, reply_markup=markup, parse_mode='HTML')
                logger.debug(f"Notification sent to user {user_id}")
            except Exception as e:
                if "Message is not modified" in str(e):
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                else:
                    raise e
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Error notifying user {user_id}: {e}")

    async def process_user_request(self, request):
        user_id = int(request.get('user_id', 0))
        task_id = request.get('task_id', '')

        if not user_id:
            logger.error("User ID missing in request")
            return

        if user_id in self.tasks and not self.tasks[user_id].done():
            logger.debug(f"Task for user {user_id} already exists.")
            return

        loop = asyncio.get_running_loop()
        task = loop.create_task(self._process_request_task(user_id, request))
        self.tasks[user_id] = task

        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task for user {user_id} was cancelled.")
        except Exception as e:
            logger.error(f"Error in task for user {user_id}: {e}")

    async def _process_request_task(self, user_id: int, request):
        try:
            logger.debug(f"Starting request processing: {request}")
            notify = request.get('notify', '0')
            status_request = request.get('status_request', 'false').lower() == 'true'

            if not status_request:
                logger.info(f"Request for user {user_id} disabled, stopping processing.")
                await self.stop_user_task(user_id)
                return

            required_keys = ['user_id', 'warehouse_ids', 'coefficient', 'supply_types']
            missing_keys = [key for key in required_keys if key not in request]
            if missing_keys:
                logger.warning(f"Missing keys {missing_keys} in request for user {user_id}")
                return

            try:
                coefficient = float(request['coefficient'])
                notify = int(notify) if notify is not None else 0
                warehouse_ids = request['warehouse_ids'].split(',')
                supply_types = request['supply_types'].split(',')
                logger.debug(f"Processing request for user_id: {user_id}, coefficient: {coefficient}, notify: {notify}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error in request data for user {user_id}: {e}")
                return

            async with self.semaphore:
                await asyncio.sleep(self.min_delay_between_requests)

                try:
                    logger.debug(f"Attempting to fetch coefficients for user {user_id}")
                    coefficients = await self.api_client.get_coefficients(warehouse_ids=warehouse_ids)
                    if not coefficients:
                        logger.info(f"No coefficients fetched for user {user_id}")
                        return
                except Exception as e:
                    logger.error(f"Error fetching coefficients for user {user_id}: {e}")
                    return

                logger.debug(f"Filtering coefficients for user {user_id}")
                filtered_coefficients = [
                    coef for coef in coefficients
                    if coef.get('warehouseID') is not None and int(coef.get('warehouseID')) in map(int, warehouse_ids)
                       and coef.get('boxTypeID') is not None and int(coef.get('boxTypeID')) in map(int, request['boxTypeID'].split(','))
                ]

                if not filtered_coefficients:
                    logger.info(f"No relevant coefficients found for request for user {user_id}")
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

                        if already_sent:
                            logger.debug(f"Message already sent to user {user_id}: {message_key}")
                        else:
                            logger.debug(f"Sending notification to user {user_id}")
                            message = (
                                f"<b>🎉 Slot found:</b>\n\n"
                                f"<i><b>Date:</b> {date}</i>\n"
                                f"<i><b>Warehouse:</b> {coef['warehouseName']}</i>\n"
                                f"<i><b>Supply Type:</b> {coef['boxTypeName']}</i>\n"
                                f"<i><b>Coefficient:</b> {coefficient_display}</i>\n"
                            )

                            await self.notify_user(user_id, message)
                            await self.redis_client.redis.set(message_key, "sent", ex=24 * 60 * 60)

                            if notify == 0:
                                logger.info(f"Request for user {user_id} completed after first notification.")
                                await self.stop_user_task(user_id)
                                return

        except Exception as e:
            logger.error(f"Error processing request for user {user_id}: {e}")

    async def stop_user_task(self, user_id: int):
        if user_id in self.tasks:
            task = self.tasks[user_id]
            if not task.done():
                task.cancel()  # Отправляем запрос на отмену задачи
                await task  # Ждем завершения задачи
            del self.tasks[user_id]  # Удаляем задачу из словаря

            logger.info(f"Task for user {user_id} successfully stopped.")
        else:
            logger.error(f"Task for user {user_id} not found.")
