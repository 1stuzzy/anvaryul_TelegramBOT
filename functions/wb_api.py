import aiohttp
import asyncio
import ssl
import certifi
from loguru import logger


class ApiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.retry_delay = 5
        self.max_retries = 5

    def get_current_token(self):
        token = self.api_key
        logger.debug(f"Используется токен: {token[:5]}...{token[-5:]}")
        return token

    async def get_coefficient(self, warehouse_ids):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        url = f"https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
        attempt = 0

        async with aiohttp.ClientSession() as session:
            while attempt < self.max_retries:
                try:
                    headers = {"Authorization": f"Bearer {self.get_current_token()}"}
                    async with session.get(url, params={"warehouse_ids": ",".join(warehouse_ids)}, headers=headers, ssl=ssl_context) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            logger.warning(f"Превышено количество запросов. Попытка {attempt + 1}")
                            attempt += 1
                            await asyncio.sleep(self.retry_delay)
                        elif response.status == 401:
                            logger.error(f"Ошибка авторизации. Проверьте токен: {headers['Authorization'][:5]}...{headers['Authorization'][-5:]}")
                            break
                        else:
                            response_text = await response.text()
                            logger.error(f"API request failed with status {response.status}: {response_text}")
                            break
                except Exception as e:
                    logger.error(f"Ошибка при запросе данных: {e}")
                    break

        logger.error(f"Не удалось получить коэффициенты после {self.max_retries} попыток.")
        return None
