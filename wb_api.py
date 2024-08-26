import aiohttp
import os
import json
from utils.config import load_config

API_URL = "https://supplies-api.wildberries.ru/api/v1/warehouses"
WAREHOUSES_FILE = "warehouses.json"
config = load_config()


# Функция для сохранения данных в JSON файл
def save_warehouses_to_json(data):
    with open(WAREHOUSES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Функция для загрузки данных из JSON файла
def load_warehouses_from_json():
    if os.path.exists(WAREHOUSES_FILE):
        with open(WAREHOUSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# Асинхронная функция для получения данных о складах из API
async def fetch_warehouses_from_api():
    headers = {
        'Authorization': f'Bearer {config.api_key}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                save_warehouses_to_json(data)  # Сохраняем данные в JSON файл
                return data
            else:
                print(f"Ошибка: {response.status}")
                return []


# Асинхронная функция для получения данных (из JSON файла или API)
async def get_warehouses():
    # Сначала пытаемся загрузить данные из JSON файла
    data = load_warehouses_from_json()
    if data:
        return data

    # Если файла нет или он пуст, делаем запрос к API
    return await fetch_warehouses_from_api()
