from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loguru import logger
from loader import config
from database.models import User
from database import postgre_base, redis_base
from data import keyboards
from data import texts

redis_client = redis_base.RedisClient(redis_url=config.redis_url)


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
                                 reply_markup=keyboards.main_keyboard())
    await message.answer(texts.menu_text,
                         reply_markup=keyboards.menu_keyboard())


async def personal_area(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = query.from_user.id
    user = User.get(User.user_id == user_id)
    subscribe_status = 'Подписка активирована' if user.subscription else 'Подписка не активирована'
    await query.message.edit_text(f'Личный кабинет\n\n'
                                  f'Статус подписки: {subscribe_status}\n'
                                  f'Дата окончания: {user.sub_date}')


async def canceled_callbacks(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()

    callback_data = query.data

    if callback_data == "back_to_request":
        await query.message.answer(texts.active_request_text,
                                   reply_markup=await keyboards.requests_keyboard(
                                       await redis_client.get_user_requests(query.from_user.id),
                                       redis_client
                                   ))
    elif callback_data == "close_callback":
        await query.message.answer_sticker(texts.hi_sticker,
                                           reply_markup=keyboards.main_keyboard())
        await query.message.answer(texts.menu_text,
                                   reply_markup=keyboards.menu_keyboard())
    elif callback_data == "back_menu":
        await query.message.answer(texts.menu_text,
                                   reply_markup=keyboards.menu_keyboard())


def register_main_menu_handlers(dp):
    dp.message_handler(commands=['start'], state='*')(send_welcome)
    dp.message_handler(Text(equals="💠 Главное меню"), state='*')(send_welcome)
    dp.callback_query_handler(lambda call: call.data in [
        'close_callback',
        'back_to_my_requests',
        'back_to_request',
        'back_menu'
    ], state='*')(canceled_callbacks)
    dp.callback_query_handler(lambda call: call.data in ['personal_area'], state='*')(personal_area)

