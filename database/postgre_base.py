from typing import Optional
from datetime import date

from database.models import User, Payment
from utils.datefunc import datetime_local_now
from loader import config


async def create_user(user_id: int, name: str, username: str, subscription: bool = False, sub_date: Optional[date] = None):
    user = User.create(
        user_id=user_id,
        name=name,
        username=username,
        subscription=subscription,
        sub_date=sub_date)
    return user


async def check_subscription(user_id: int) -> bool:
    user = User.get(User.user_id == user_id)
    if user:
        return user.subscription
    return False


async def create_payment(user_id: int, summ: int, payment_status: bool = False):
    """
    Создает новую запись платежа для пользователя.

    :param user_id: ID пользователя
    :param summ: Сумма платежа
    :param payment_status: Статус платежа (по умолчанию False)
    :param payment_date: Дата платежа (по умолчанию текущая дата)
    :return: Объект Payment
    """

    user = User.get(User.user_id == user_id)
    payment = Payment.create(
        user=user,
        date=datetime_local_now().strftime('%d.%m.%Y %H:%M'),
        summ=summ,
        payment_status=payment_status
    )
    return payment