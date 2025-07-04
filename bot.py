import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
from menu import main_menu
from profile import register_user_if_needed, user_profiles

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start_handler(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_profiles:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton(text="📋 Зарегистрироваться"))
        await message.answer("👋 Привет! Добро пожаловать в PhysIQ. Пожалуйста, зарегистрируйся, чтобы начать!", reply_markup=kb)
    else:
        await message.answer(f"С возвращением, {user_profiles[user_id]['first_name']}!", reply_markup=main_menu)

@dp.message(F.text == "📋 Зарегистрироваться")
async def begin_register(message: types.Message):
    await register_user_if_needed(message, bot)

@dp.message()
async def fallback(message: types.Message):
    await message.answer("👀 Я тебя не понял. Нажми /start.")

async def on_startup(dispatcher):
    print("📡 Устанавливаем webhook...")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dispatcher):
    await bot.delete_webhook()

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)

