from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button = KeyboardButton("Получить список складов")
    search_button = KeyboardButton("Поиск склада")
    keyboard.add(button, search_button)
    return keyboard
