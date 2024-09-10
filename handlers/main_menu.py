from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loguru import logger
from database.models import User
from database import postgre_base
from data.keyboards.main_kbs import main_keyboard, menu_keyboard
from data import texts


async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    name = message.from_user.full_name
    username = message.from_user.username

    try:
        logger.debug(f"[{user_id}:{name}], in base info updated")
        user = User.get(User.user_id == user_id)
        if user.name != name or user.username != username:
            user.name = name
            user.username = username
            user.save()
    except User.DoesNotExist:
        logger.debug(f"[{user_id}:{name}], first time /start to bot")
        await postgre_base.create_user(user_id=user_id,
                                       name=name,
                                       username=username)

    await message.answer_sticker(texts.hi_sticker,
                                 reply_markup=main_keyboard())
    await message.answer(texts.menu_text,
                         reply_markup=menu_keyboard())


def register_main_menu_handlers(dp):
    dp.message_handler(commands=['start'], state='*')(send_welcome)
    dp.message_handler(Text(equals="💠 Главное меню"), state='*')(send_welcome)
