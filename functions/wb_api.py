import aiohttp
import asyncio
from loguru import logger


class ApiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_token_index = 0
        self.max_retries = len(api_key) * 2
        self.retry_delay = 5

    def get_current_token(self):
        return self.api_key[self.current_token_index]

    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.api_key)

    async def get_coefficients(self, warehouse_ids):
        url = f"https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
        attempt = 0

        async with aiohttp.ClientSession() as session:
            while attempt < self.max_retries:
                try:
                    headers = {"Authorization": f"Bearer {self.get_current_token()}"}
                    async with session.get(url, params={"warehouse_ids": ",".join(warehouse_ids)}, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            self.switch_token()
                            attempt += 1
                            await asyncio.sleep(self.retry_delay)
                        elif response.status == 401:
                            logger.warning("Ошибка авторизации, переключение токена.")
                            self.switch_token()
                            attempt += 1
                        else:
                            response_text = await response.text()
                            raise Exception(f"API request failed with status {response.status}: {response_text}")
                except Exception as e:
                    logger.error(f"Ошибка при запросе данных: {e}")
                    return None

        logger.error(f"Не удалось получить коэффициенты после {self.max_retries} попыток.")
        return None

    async def fetch_warehouses(self):
        url = 'https://supplies-api.wildberries.ru/api/v1/warehouses'
        headers = {"Authorization": f"Bearer {self.get_current_token()}"}

        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            self.switch_token()
                            await asyncio.sleep(1)
                        elif response.status == 401:
                            logger.warning("Ошибка авторизации, переключение токена.")
                            self.switch_token()
                        else:
                            response_text = await response.text()
                            logger.error(f"Ошибка при получении данных: {response.status} - {response_text}")
                            return None
                except Exception as e:
                    logger.error(f"Ошибка при запросе данных: {e}")
                    return None

    async def check_coefficient(self, session, user_id, alert_params):
        """Функция для выполнения запроса к API WB и получения коэффициента."""
        url = 'https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients'
        headers = {"Authorization": f"Bearer {self.get_current_token()}"}

        while True:
            try:
                async with session.get(url, params=alert_params, headers=headers) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data.get("coefficient")
                    elif response.status == 429:
                        self.switch_token()
                        await asyncio.sleep(1)
                    elif response.status == 401:
                        logger.warning("Ошибка авторизации, переключение токена.")
                        self.switch_token()
                    else:
                        response_text = await response.text()
                        logger.error(f"Ошибка при запросе данных: {response.status} - {response_text}")
                        return None
            except Exception as e:
                logger.error(f"Ошибка при запросе коэффициента для пользователя {user_id}: {e}")
                return None

    async def parse_warehouses(self):
        """Запрос и парсинг информации о складских центрах."""
        data = await self.fetch_warehouses()
        if data:
            return [{"id": warehouse["ID"], "name": warehouse["name"]} for warehouse in data]
        else:
            return []
