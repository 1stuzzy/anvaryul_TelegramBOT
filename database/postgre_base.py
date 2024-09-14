from typing import Optional
from datetime import datetime, timedelta, date

from database.models import User, Payment, Subscription
from utils.datefunc import normalized_local_now
from loader import config


async def create_user(user_id: int, name: str, username: str, subscription: bool = False, sub_date: Optional[date] = None):
    user = User.create(
        user_id=user_id,
        name=name,
        username=username,
        subscription=subscription,
        sub_date=sub_date)
    return user


def check_subscription(user: User) -> Optional[Subscription]:
    """
    Возвращает активную подписку пользователя, если она существует.

    :param user: Экземпляр модели User
    :return: Активная подписка (Subscription) или None, если активной подписки нет
    """
    return (Subscription
            .select()
            .where(
        (Subscription.user == user) &
        (Subscription.is_active == True))
            .order_by(Subscription.end_date.desc())
            .first())


async def create_payment(user_id: int, summ: int, payment_status: bool = False):
    """
    Создает новую запись платежа для пользователя.

    :param user_id: ID пользователя
    :param summ: Сумма платежа
    :param payment_status: Статус платежа (по умолчанию False)
    :return: Объект Payment
    """

    user = User.get(User.user_id == user_id)

    payment_date = normalized_local_now().strftime('%Y-%m-%d %H:%M:%S')

    payment = Payment.create(
        user=user,
        date=payment_date,
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


async def grant_subscription(user_id: int, sub_days: int):
    user = User.get_or_none(User.user_id == user_id)
    if not user:
        return

    now = normalized_local_now()
    active_subscription = check_subscription(user)

    if active_subscription and active_subscription.end_date:
        new_end_date = active_subscription.end_date + timedelta(days=sub_days)
        active_subscription.end_date = new_end_date
        active_subscription.save()
        return active_subscription  # Возвращаем обновленную подписку
    else:
        new_end_date = now + timedelta(days=sub_days)
        new_subscription = Subscription.create(
            user=user,
            start_date=now,
            end_date=new_end_date,
            is_active=True
        )
        return new_subscription  # Возвращаем новую подписку



async def update_subscription_status(user_id: int, additional_days: int):
    """
    Проверяет и обновляет статус подписки пользователя, добавляя дни к текущей дате подписки, если она активна,
    или устанавливая новую дату, если подписка истекла.

    :param user_id: ID пользователя
    :param additional_days: Количество дней, на которое продлевается подписка
    :return: Обновленный объект User или None, если пользователь не найден
    """
    try:
        user = await User.get(User.user_id == user_id)

        # Проверяем, если подписка активна и еще не истекла
        if user.sub_date and user.sub_date >= normalized_local_now().date():
            # Продлеваем подписку
            user.sub_date += timedelta(days=additional_days)
        else:
            # Устанавливаем новую дату подписки, начиная с сегодняшнего дня
            user.sub_date = normalized_local_now().date() + timedelta(days=additional_days)

        user.subscription = True  # Активируем подписку
        await user.save()  # Сохраняем изменения в базе данных
        return user

    except User.DoesNotExist:
        print(f"Пользователь с ID {user_id} не найден.")
        return None

    except Exception as e:
        print(f"Произошла ошибка при обновлении статуса подписки: {e}")
        return None