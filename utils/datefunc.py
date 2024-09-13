from datetime import datetime, time, timedelta
import pytz

from .config import load_config

config = load_config()
local_tz = pytz.timezone(config.time_zone)


def normalized_local_now():  # use with tzinfo
    local_dt = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def datetime_local_now():  # usable for peewee datetimefield
    return normalized_local_now().replace(tzinfo=None)  # return datetime instance


def calculate_dates(days_to_add: int):
    """Вычисляет стартовую и конечную даты на основе количества дней, которые нужно добавить."""
    start_date = datetime_local_now().strftime('%d.%m.%Y %H:%M')

    if days_to_add == 0:
        end_date = datetime.combine(datetime_local_now().date(), time(23, 59, 59)).strftime('%d.%m.%Y %H:%M')
    else:
        end_date = (datetime_local_now() + timedelta(days=days_to_add)).strftime('%d.%m.%Y %H:%M')

    return start_date, end_date