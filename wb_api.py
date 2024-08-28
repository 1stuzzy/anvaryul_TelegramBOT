import aiohttp
from loader import config
from loguru import logger


async def get_warehouses():
    headers = {
        'Authorization': f'Bearer {config.api_key}'
    }
    url = "https://supplies-api.wildberries.ru/api/v1/warehouses"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Ошибка при запросе к API: {response.status}")
                    return []
        except Exception as e:
            logger.exception(f"Произошла ошибка при запросе к API: {e}")
            return []


async def get_coefficients(warehouse_id=None):
    headers = {
        'Authorization': f'Bearer {config.api_key}'
    }
    params = {}
    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    if warehouse_id:
        # Предполагаем, что warehouse_id может быть как числом, так и списком чисел
        if isinstance(warehouse_id, list):
            params['warehouseIDs'] = ','.join(map(str, warehouse_id))
        else:
            params['warehouseIDs'] = str(warehouse_id)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Ошибка при запросе к API: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            logger.exception(f"Произошла ошибка при запросе к API: {e}")
            return None


async def test_get_coefficients():
    # Проверка с одним складом
    result_single = await get_coefficients(6156)
    print("Коэффициенты для одного склада:", result_single)

    # Проверка с несколькими складами
    result_multiple = await get_coefficients([6156, 507])
    print("Коэффициенты для нескольких складов:", result_multiple)

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_get_coefficients())