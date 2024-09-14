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
    reg_date = DateTimeField(default=datetime_local_now())


class Payment(BaseModel):
    payment_id = AutoField()
    user = ForeignKeyField(User, backref='payment', on_delete='CASCADE')
    date = DateField()
    summ = BigIntegerField()
    payment_status = BooleanField(default=False)


class Subscription(BaseModel):
    user = ForeignKeyField(User, backref='subscriptions', on_delete='CASCADE')
    start_date = DateTimeField(null=False)
    end_date = DateTimeField(null=False)
    is_active = BooleanField(default=True)


def connect():
    base.connect()
    base.create_tables(
        [
        User,
        Payment,
        Subscription
        ]
    )


def disconnect():
    base.close()
