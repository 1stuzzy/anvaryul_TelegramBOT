from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import ChatNotFound, UserDeactivated, BotKicked

from loguru import logger
from loader import config, dp
from database.models import User
from database import postgre_base, redis_base
from data import keyboards, texts

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
        await postgre_base.create_user(user_id=user_id, name=name, username=username)

    if await check_chat_subscription(user_id, config.chat_id):
        await message.answer_sticker(texts.hi_sticker, reply_markup=keyboards.main_keyboard())
        await message.answer(texts.menu_text, reply_markup=keyboards.menu_keyboard())
    else:
        await message.answer(texts.not_subscribed_text,
                             reply_markup=keyboards.subscription_required(config.chat_url))


async def personal_area(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = query.from_user.id

    user = User.get(User.user_id == user_id)

    active_subscription = postgre_base.check_subscription(user)

    if active_subscription:
        subscribe_status = 'Подписка активирована'
        end_date = active_subscription.end_date.strftime('%d.%m.%Y %H:%M')
        end_date_text = f"<b>└ Активна до:</b> <i>{end_date}</i>"
    else:
        subscribe_status = 'Подписка не активирована'
        end_date_text = ''

    await query.message.edit_text(
        texts.personal_area.format(
            subscribe_status=subscribe_status,
            end_date=end_date_text
        ),
        reply_markup=keyboards.back()
    )


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


async def check_chat_subscription(user_id: int, chat_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на указанный чат.

    :param user_id: ID пользователя
    :param chat_id: ID чата
    :return: True, если пользователь подписан, иначе False
    """
    try:
        member = await dp.bot.get_chat_member(chat_id, user_id)
        # Проверяем, что пользователь не является покинувшим или выгнанным из чата
        return member.status in ['member', 'administrator', 'creator']
    except (ChatNotFound, UserDeactivated, BotKicked) as e:
        logger.error(f"Ошибка при проверке подписки на чат: {e}")
        return False


async def handle_check_subscription(query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает запрос на проверку подписки пользователя на чат сообщества.

    :param query: CallbackQuery от пользователя
    :param state: Состояние FSM
    """
    user_id = query.from_user.id
    chat_id = config.chat_id  # Используй ID чата из конфигурации

    is_subscribed = await check_chat_subscription(user_id, chat_id)

    if is_subscribed:
        await query.message.edit_text(texts.menu_text, reply_markup=keyboards.menu_keyboard())
    else:
        await query.message.edit_text(texts.not_subscribed_text,
                                      reply_markup=keyboards.subscription_required(config.chat_url))


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
    dp.register_callback_query_handler(handle_check_subscription, lambda call: call.data == "check_subscription")
