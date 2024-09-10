import asyncio
import aiohttp

from loguru import logger
from loader import config


class ApiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_token_index = 0
        self.max_retries = len(api_key) * 2
        self.retry_delay = 5

    def get_current_token(self):
        logger.debug(f"Используется токен с индексом {self.current_token_index}")
        return self.api_key[self.current_token_index]

    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.api_key)
        logger.debug(f"Переключение на токен с индексом {self.current_token_index}")

    async def get_coefficient(self, session, user_id, alert_params):
        """Функция для выполнения запроса к API WB и получения коэффициента."""
        url = f'{config.base_url}/acceptance/coefficients'
        headers = {"Authorization": f"Bearer {self.get_current_token()}"}

        while True:
            try:
                async with session.get(url, params=alert_params, headers=headers) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data.get("coefficient")
                    elif response.status == 429:
                        logger.warning("Превышено количество запросов, переключение токена.")
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

    async def get_coefficients(self, warehouse_ids):
        """Функция для получения коэффициентов для списка складов."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.get_coefficient(session, user_id=None, alert_params={"warehouse_id": wid})
                for wid in warehouse_ids
            ]
            results = await asyncio.gather(*tasks)
            coefficients = [
                {"warehouseID": wid, "coefficient": coef}
                for wid, coef in zip(warehouse_ids, results) if coef is not None
            ]
            return coefficients
