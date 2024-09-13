from peewee import *
from playhouse.shortcuts import ReconnectMixin
from playhouse.postgres_ext import PostgresqlExtDatabase

from utils.datefunc import datetime_local_now
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


class User(BaseModel):
    user_id = BigIntegerField(unique=True, index=True, primary_key=True)
    name = CharField(max_length=255)
    username = CharField(max_length=255, unique=True, index=True)
    subscription = BooleanField(default=False)
    sub_date = DateField(null=True)
    reg_date = DateTimeField(default=datetime_local_now())


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
