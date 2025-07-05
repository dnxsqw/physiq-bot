from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧠 Решать задачи")],
        [KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏆 Ачивки"), KeyboardButton(text="🎯 Рейтинг")]
    ],
    resize_keyboard=True
)
