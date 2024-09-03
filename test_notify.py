import pytest
from unittest.mock import AsyncMock
from functions.task_notify import NotificationService


@pytest.mark.asyncio
async def test_notify_user():
    bot = AsyncMock()
    redis_client = AsyncMock()
    api_client = AsyncMock()

    service = NotificationService(api_client, redis_client, bot)

    await service.notify_user(user_id=5889390958, new_coefficient=1.5)

    bot.send_message.assert_called_once_with(123, "Уведомление: коэффициент по вашему запросу изменился на 1.50")
