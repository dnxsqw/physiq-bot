from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎯 Решать!")],
    [KeyboardButton(text="📊 Рейтинг"), KeyboardButton(text="🏆 Ачивки")],
    [KeyboardButton(text="📚 Мои задачи"), KeyboardButton(text="📅 Стрик")]
], resize_keyboard=True)
