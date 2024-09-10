from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import config
from data.keyboards.main_kbs import support_keyboard
from data import texts


async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    support = config.support
    await message.answer(texts.support_text,
                         reply_markup=support_keyboard(support))


def register_support_handlers(dp):
    dp.message_handler(Text(equals="👨‍💻 Техническая поддержка"), state='*')(process_support)
