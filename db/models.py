from peewee import *
from playhouse.shortcuts import ReconnectMixin
from playhouse.postgres_ext import PostgresqlExtDatabase
from datetime import datetime


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


class User(BaseModel):
    user_id = BigIntegerField(unique=True, index=True, primary_key=True)  # Уникальный идентификатор
    name = CharField(max_length=255)
    username = CharField(max_length=255, unique=True, index=True)  # username также должен быть уникальным
    subscription = BooleanField(default=False)
    sub_date = DateField(null=True)
    reg_date = DateTimeField(default=datetime.now().strftime('%d.%m.%y %H:%M'))


class Payment(BaseModel):
    payment_id = AutoField()
    user = ForeignKeyField(User, backref='payment', on_delete='CASCADE')
    date = DateField()
    summ = BigIntegerField()
    payment_status = BooleanField(default=False)


def connect():
    base.connect()
    base.create_tables(
        [
        User,
        Payment
        ]
    )


def disconnect():
    base.close()
