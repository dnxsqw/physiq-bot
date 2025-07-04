import os
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

async def main():
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook установлен!")

if __name__ == "__main__":
    asyncio.run(main())
