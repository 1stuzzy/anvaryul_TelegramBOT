from time import time


def check_timing(func):
    def wrapper(*args, **kwargs):
        time_now = time()
        result = func(*args, **kwargs)
        print(time() - time_now)
        return result

    return wrapper


def async_check_timing(func):
    async def wrapper(*args, **kwargs):
        time_now = time()
        result = await func(*args, **kwargs)
        print(time() - time_now)
        return result

    return wrapper
