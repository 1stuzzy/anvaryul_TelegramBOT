from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.utils.markdown import text as md_text
from aiogram.types import ParseMode

import json
from loguru import logger
from utils.config import save_config
from loader import config
from functions.executional import is_admin


async def set_requisites_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    new_requisites = message.get_args().strip()

    if not new_requisites:
        await message.reply("<i>Укажите новые реквизиты\n\n"
                            "Пример: /set_requisites 00000</i>", parse_mode=ParseMode.HTML)
        return

    # Обновляем значение в config
    config.requisites = new_requisites

    # Сохраняем изменения в JSON файл
    save_config(config)

    logger.info(f"Администратор {message.from_user.id} изменил реквизиты на: {new_requisites}")

    await message.reply(f"<b>Реквизиты успешно обновлены ✅</b>\n\n"
                        f"<b>💳 Новые реквизиты:</b>\n"
                        f"{new_requisites}")


def register_admin_handlers(dp):
    dp.message_handler(Command("set_requisites"))(set_requisites_handler)