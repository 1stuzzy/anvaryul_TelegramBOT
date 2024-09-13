from aiogram import types
from aiogram.dispatcher import FSMContext

from data import keyboards
from data import texts


async def process_faq(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text(texts.faq_text,
                                  reply_markup=keyboards.close_btn())


def register_faq_handlers(dp):
    dp.callback_query_handler(lambda call: call.data == 'faq', state='*')(process_faq)

