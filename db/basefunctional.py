import aiohttp
from peewee import IntegrityError
from db.models import Warehouse
from peewee import DoesNotExist
from loguru import logger
from loader import load_config

#def parse_warehouse(warehouse_id: int, name: str, address: str):
    #try:
        #warehouse, created = Warehouse.get_or_create(
            #warehouse_id=warehouse_id,
            #defaults={'name': name, 'address': address}
        #)
        #if created:
            #logger.info(f"Склад {name} успешно добавлен в базу данных.")
        #else:
            #logger.info(f"Склад {name} уже существует в базе данных.")
        #return warehouse
    #except IntegrityError as e:
        #logger.error(f"Ошибка целостности данных при добавлении склада {name}: {e}")
        #return None
    #except Exception as e:
        #logger.exception(f"Произошла ошибка при добавлении склада {name}: {e}")
        #return None

import psycopg2
config = load_config()


def get_warehouses():
    """Прямое выполнение SQL-запроса через psycopg2."""
    try:
        conn = psycopg2.connect(
            dbname=config.db.database,
            user=config.db.user,
            password=config.db.password,
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM warehouse")
        results = cur.fetchall()

        if not results:
            print("Склады не найдены.")
        else:
            print(f"Найдено {len(results)} складов:")
            for row in results:
                print(f"ID={row[0]}, Name={row[1]}")

        cur.close()
        conn.close()

        return [{"id": row[0], "name": row[1]} for row in results]
    except Exception as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return []


async def add_warehouses():
    warehouses = await get_warehouses()

    if warehouses:
        for wh in warehouses:
            warehouse_id = wh.get('ID')
            name = wh.get('name')
            address = wh.get('address')

            if warehouse_id and name and address:
                parse_warehouse(warehouse_id=warehouse_id, name=name, address=address)
            else:
                logger.warning(f"Неполные данные для склада: {wh}")
    else:
        logger.error('Не удалось получить данные через API!')


def get_warehouse_by_id(warehouse_id: int):
    try:
        warehouse = Warehouse.get(Warehouse.warehouse_id == warehouse_id)
        return warehouse
    except DoesNotExist:
        logger.error(f"Склад с ID {warehouse_id} не найден в базе данных.")
        return None
