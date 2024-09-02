import aiohttp
from peewee import IntegrityError
from db.models import Warehouses
from peewee import DoesNotExist
from loguru import logger
from loader import load_config
import psycopg2
config = load_config()

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
        cur.execute("SELECT warehouse_id, name FROM warehouses")
        results = cur.fetchall()

        cur.close()
        conn.close()

        return [{"id": row[0], "name": row[1]} for row in results]
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return []


def get_warehouse_by_id(warehouse_id: int):
    try:
        warehouse = Warehouses.get(Warehouses.warehouse_id == warehouse_id)
        return warehouse
    except DoesNotExist:
        logger.error(f"Склад с ID {warehouse_id} не найден в базе данных.")
        return None


def get_warehouse_name(warehouse_id: int) -> str:
    try:
        conn = psycopg2.connect(
            dbname=config.db.database,
            user=config.db.user,
            password=config.db.password,
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute("SELECT name FROM warehouses WHERE id = %s", (warehouse_id,))
        result = cur.fetchone()

        cur.close()
        conn.close()

        if result:
            return result[0]  # Возвращаем название склада
        else:
            logger.error(f"Склад с ID {warehouse_id} не найден в базе данных.")
            return f"Неизвестный склад (ID: {warehouse_id})"
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса к базе данных: {e}")
        return f"Ошибка базы данных (ID: {warehouse_id})"