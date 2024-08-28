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


class Warehouse(BaseModel):
    warehouse_id = IntegerField(unique=True, index=True)
    name = CharField(max_length=255)
    address = TextField()


class UserTasks(BaseModel):
    user_id = IntegerField(unique=True, index=True)
    name = CharField(max_length=255)
    params = TextField()
    task_id = IntegerField(unique=True)


def connect():
    base.connect()
    base.create_tables(
        [
            Warehouse,
            UserTasks
        ]
    )


def disconnect():
    base.close()
