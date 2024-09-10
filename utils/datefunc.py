from datetime import datetime

import pytz

from .config import load_config

config = load_config()
local_tz = pytz.timezone(config.time_zone)


def normalized_local_now():  # use with tzinfo
    local_dt = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def datetime_local_now():  # usable for peewee datetimefield
    return normalized_local_now().replace(tzinfo=None)  # return datetime instance
