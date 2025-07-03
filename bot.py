import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from menu import main_menu

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message):
    await message.answer("👋 Привет! Я — PhysIQ, твой помощник по олимпиадной физике.", reply_markup=main_menu)

@dp.message(F.text == "🎯 Решать!")
async def solve(message):
    await message.answer("📌 Задача дня:\n\nЧто будет, если на манула подействует сила в 10 Н в течение 3 секунд?")

@dp.message()
async def fallback(message):
    await message.answer("👀 Я тебя не понял. Нажми /start.")

async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dispatcher):
    await bot.delete_webhook()

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)
