from peewee import *
from playhouse.shortcuts import ReconnectMixin
from playhouse.postgres_ext import PostgresqlExtDatabase

from loader import load_config

config = load_config()


class DB(ReconnectMixin, PostgresqlExtDatabase):
    pass


base = DB(
    database=config.db.database,
    user=config.db.user,
    password=config.db.password,
    host="localhost",
    port=5432,
)


class BaseModel(Model):
    class Meta:
        database = base


class Warehouses(BaseModel):
    warehouse_id = IntegerField(unique=True, index=True)
    name = CharField(max_length=255)
    address = TextField()


class UserRequest(BaseModel):  # Наследуем от BaseModel, а не Model
    user_id = BigIntegerField()  # Измените на BigIntegerField
    warehouse_ids = CharField()  # Сохраняем в виде строки, например: "1733, 303295"
    supply_types = CharField()  # Сохраняем в виде строки, например: "qr_supply, boxes"
    coefficient = CharField()  # Сохраняем выбранный коэффициент
    period = CharField()  # Период
    notification_type = CharField()
    activate = BooleanField(default=False)


def connect():
    base.connect()
    base.create_tables(
        [
            Warehouses,
            UserRequest
        ]
    )


def disconnect():
    base.close()
