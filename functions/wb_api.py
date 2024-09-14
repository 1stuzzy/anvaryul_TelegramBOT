import aiohttp
import asyncio
from loguru import logger


class ApiClient:
    def __init__(self, api_keys, max_retries=5, retry_delay=2, rate_limit=10):
        self.api_keys = api_keys  # Список API ключей
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.current_key_index = 0

    def get_current_key(self):
        """Получение текущего API ключа."""
        return self.api_keys[self.current_key_index]

    def switch_to_next_key(self):
        """Переключение на следующий API ключ."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Переключение на следующий API ключ: {self.get_current_key()[:5]}...")

    async def get_coefficient(self, warehouse_ids):
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                async with self.semaphore:
                    try:
                        headers = {"Authorization": f"Bearer {self.get_current_key()}"}
                        url = f"https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
                        async with session.get(url, params={"warehouse_ids": ",".join(warehouse_ids)}, headers=headers) as response:
                            if response.status == 200:
                                logger.info(f"Запрос к API успешен, попытка {attempt + 1}")
                                return await response.json()
                            elif response.status == 429:
                                logger.warning(f"Превышен лимит запросов для ключа: {self.get_current_key()[:5]}..., переключение на другой ключ.")
                                self.switch_to_next_key()
                                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Экспоненциальная задержка
                            else:
                                logger.error(f"Ошибка при запросе к API: {response.status}")
                                await asyncio.sleep(self.retry_delay)
                    except Exception as e:
                        logger.error(f"Ошибка при выполнении запроса: {e}")
                        await asyncio.sleep(self.retry_delay)

            logger.error(f"Не удалось получить данные после {self.max_retries} попыток.")
            return None