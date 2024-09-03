from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware


class RedisMiddleware(BaseMiddleware):
    def __init__(self, redis_client):
        super().__init__()
        self.redis_client = redis_client

    async def on_process_callback_query(self, query: types.CallbackQuery, data: dict):
        data['redis_client'] = self.redis_client

    async def on_process_message(self, message: types.Message, data: dict):
        data['redis_client'] = self.redis_client