from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import config
from data import texts, keyboards


async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(texts.support_text,
                         reply_markup=keyboards.subscription_required(config.chat_url))


def register_support_handlers(dp):
    dp.message_handler(Text(equals="👨‍💻 Техническая поддержка"), state='*')(process_support)
