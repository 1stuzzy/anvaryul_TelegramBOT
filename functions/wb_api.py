import aiohttp
import asyncio
from loguru import logger


class ApiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"{self.api_key}"}

    async def fetch_warehouses(self):
        url = 'https://supplies-api.wildberries.ru/api/v1/warehouses'
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Ошибка при получении данных: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                logger.error(f"Ошибка при запросе данных: {e}")
                return None

    async def get_coefficients(self, warehouse_ids):
        url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
        params = {'warehouseIDs': ','.join(map(str, warehouse_ids))}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.error(f"Превышен лимит запросов к API: {await response.text()}")
                        await asyncio.sleep(60)
                        return None
                    else:
                        logger.error(f"Ошибка при запросе к API: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                logger.exception(f"Произошла ошибка при запросе к API: {e}")
                return None

    async def check_coefficient(self, session, user_id, alert_params):
        """Функция для выполнения запроса к API WB и получения коэффициента."""
        url = 'https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients'
        try:
            async with session.get(url, params=alert_params) as response:
                response_data = await response.json()
                return response_data.get("coefficient")
        except Exception as e:
            logger.error(f"Ошибка при запросе коэффициента для пользователя {user_id}: {e}")
            return None

    async def parse_warehouses(self):
        """Запрос и парсинг информации о складских центрах."""
        data = await self.fetch_warehouses()
        if data:
            # Используем правильные ключи для извлечения ID и имени склада
            return [
                {"id": warehouse["ID"], "name": warehouse["name"]}
                for warehouse in data
            ]
        else:
            return []