from typing import Optional
from datetime import datetime, timedelta, date
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


async def set_pay_status(user_id: int, new_status: bool):
    """
    Обновляет статус последней записи платежа для пользователя.

    :param user_id: ID пользователя
    :param new_status: Новый статус платежа
    :return: Обновленный объект Payment или None, если запись не найдена
    """
    try:
        payment = Payment.select().where(Payment.user_id == user_id).order_by(Payment.date.desc()).get()

        payment.payment_status = new_status
        payment.save()

        return payment

    except Payment.DoesNotExist:
        return None

    except Exception:
        return None


async def set_sub_status(user_id: int, new_status: bool):
    """
    Обновляет статус последней записи платежа для пользователя.

    :param user_id: ID пользователя
    :param new_status: Новый статус платежа
    :return: Обновленный объект Payment или None, если запись не найдена
    """
    try:
        payment = Payment.select().where(Payment.user_id == user_id).order_by(Payment.date.desc()).get()

        payment.payment_status = new_status
        payment.save()

        return payment

    except Payment.DoesNotExist:
        return None

    except Exception:
        return None


async def grant_subscription(user_id: int, days_to_extend: int):
    """
    Выдает или продлевает подписку пользователю.

    :param user_id: ID пользователя
    :param days_to_extend: Количество дней, на которые следует продлить подписку
    :return: Обновленный объект User
    """
    try:
        user = User.get(User.user_id == user_id)

        if user.subscription and user.sub_date and user.sub_date > datetime.now().date():
            user.sub_date = user.sub_date + timedelta(days=days_to_extend)
        else:
            user.sub_date = datetime.now().date() + timedelta(days=days_to_extend)
            user.subscription = True

        return user

    except User.DoesNotExist:
        print(f"Пользователь с ID {user_id} не найден.")
        return None

    except Exception as e:
        print(f"Произошла ошибка при обновлении подписки: {e}")
        return None


async def update_subscription_status(user_id: int):
    """
    Проверяет и обновляет статус подписки пользователя, если она истекла.

    :param user_id: ID пользователя
    :return: Обновленный объект User или None, если пользователь не найден
    """
    try:
        user = await User.get(User.user_id == user_id)

        if user.sub_date and user.sub_date < datetime.now().date():
            user.subscription = False
            user.save()
        return user

    except User.DoesNotExist:
        print(f"Пользователь с ID {user_id} не найден.")
        return None

    except Exception as e:
        print(f"Произошла ошибка при обновлении статуса подписки: {e}")
        return None
