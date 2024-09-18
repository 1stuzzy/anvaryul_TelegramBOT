from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


"""""
Состояния
"""""


class PaymentVerification(StatesGroup):
    receipt = State()

