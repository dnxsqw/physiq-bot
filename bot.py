import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from menu import main_menu
from profile import router as profile_router, user_profiles

from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state

# Загрузка переменных
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Инициализация бота
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(profile_router)  # FSM-регистрация

# Старт
@dp.message(F.text == "/start")
async def start_handler(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in user_profiles:
        kb = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="📋 Зарегистрироваться")]],
            resize_keyboard=True
        )
        await message.answer(
            "👋 Привет! Добро пожаловать в PhysIQ. Пожалуйста, зарегистрируйся, чтобы начать!",
            reply_markup=kb
        )
    else:
        await message.answer(
            f"С возвращением, {user_profiles[user_id]['first_name']}!",
            reply_markup=main_menu
        )

# ⛔ fallback — только если пользователь НЕ в FSM
@dp.message(StateFilter(default_state))
async def fallback(message: types.Message):
    await message.answer("👀 Я тебя не понял. Нажми /start.")

# Webhook
async def on_startup(dispatcher: Dispatcher):
    print("📡 Устанавливаем webhook...")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dispatcher: Dispatcher):
    await bot.delete_webhook()

# Запуск на Render
app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)
