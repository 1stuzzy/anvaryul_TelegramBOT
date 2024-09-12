from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loguru import logger
from loader import config
from database.models import User
from database import postgre_base
from data.keyboards import keyboard
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
                                 reply_markup=keyboard.main_keyboard())
    await message.answer(texts.menu_text,
                         reply_markup=keyboard.menu_keyboard())

async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    support = config.support
    await message.answer(texts.support_text, reply_markup=keyboard.support_keyboard(support))

async def process_faq(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text(texts.faq_text, reply_markup=None)

async def process_subscribe(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if query.data == 'subscribe':
        await query.message.edit_text(texts.subscribe_text, reply_markup=keyboard.subscribe_kb())
    else:
        await query.answer(texts.exception_sub_text, show_alert=True)
        await query.message.edit_text(texts.subscribe_text, reply_markup=keyboard.subscribe_kb())

def register_main_menu_handlers(dp):
    dp.message_handler(commands=['start'], state='*')(send_welcome)
    dp.message_handler(Text(equals="💠 Главное меню"), state='*')(send_welcome)
    dp.message_handler(Text(equals="👨‍💻 Техническая поддержка"), state='*')(process_support)
    dp.callback_query_handler(lambda call: call.data == 'faq')(process_faq)
    dp.callback_query_handler(lambda call: call.data == 'subscribe' or call.data == 'not_subscribe')(process_subscribe)
