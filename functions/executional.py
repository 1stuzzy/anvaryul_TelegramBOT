from data import texts
from database.models import User, Subscription
from loader import config
from utils.datefunc import normalized_local_now


def get_supply_name(boxTypeID):
    """Возвращает название типа поставки по ID."""
    if not boxTypeID:
        return 'Unknown Type'

    boxTypeIDs = boxTypeID.split(',')
    supply_names = []

    for box_id in boxTypeIDs:
        try:
            boxTypeID_int = int(box_id)
        except ValueError:
            return 'Unknown Type'

        found = False
        for name, (_, type_id) in texts.types_map.items():
            if type_id == boxTypeID_int:
                supply_names.append(name)
                found = True
                break

        if not found:
            supply_names.append('Unknown Type')

    return ', '.join(supply_names)


def check_subscriptions():
    now = normalized_local_now()

    expired_subscriptions = Subscription.select().where(
        (Subscription.end_date <= now) &
        (Subscription.is_active == True)
    )

    if expired_subscriptions.exists():
        for subscription in expired_subscriptions:

            subscription.is_active = False
            subscription.save()
    else:
        return True


def is_admin(user_id: int) -> bool:
    return user_id in config.admins_id