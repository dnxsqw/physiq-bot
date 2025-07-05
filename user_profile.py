import json
import os
import logging
from aiogram import Router, types
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from oauth2client.service_account import ServiceAccountCredentials
import gspread

router = Router()

# Путь к файлу с профилями
USERS_FILE = "users.json"

# Путь к ключу сервисного аккаунта
GOOGLE_JSON_KEYFILE = "physiq-bot-bb4835247b64.json"

# Загрузка профилей
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        user_profiles = json.load(f)
else:
    user_profiles = {}

# Состояния регистрации
class Register(StatesGroup):
    first_name = State()
    last_name = State()
    city = State()
    school = State()
    grade = State()

def normalize_school(school: str) -> str:
    return school.lower().capitalize().replace("школа", "Школа").replace("лицей", "Лицей")

def save_profiles():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_profiles, f, ensure_ascii=False, indent=2)
    logging.debug("✅ Профиль сохранён в users.json")

def sync_to_google(user_id: str):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_KEYFILE, scope)
        client = gspread.authorize(creds)

        sheet = client.open("PhysIQ Users").sheet1
        profile = user_profiles[user_id]
        row = [
            user_id,
            profile["username"],
            profile["first_name"],
            profile["last_name"],
            profile["city"],
            profile["school"],
            profile["normalized_school"],
            profile["class"],
            str(profile["manuls"]),
            str(profile["streak"]),
            str(profile["solved"]),
            ", ".join(profile["achievements"])
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        logging.debug("✅ Профиль синхронизирован с Google Sheets")
    except Exception as e:
        logging.warning(f"[Google Sync Error] ❌ {e}")

# 💡 Важно: finish_registration должен быть определён ДО вызова
async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = str(message.from_user.id)

    profile = {
        "username": message.from_user.username or "",
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "city": data["city"],
        "school": data["school"],
        "normalized_school": normalize_school(data["school"]),
        "class": data["grade"],
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }
    user_profiles[user_id] = profile
    logging.debug(f"[DEBUG] Новый профиль создан: {profile}")
    save_profiles()
    sync_to_google(user_id)

    await message.answer("🎉 Регистрация завершена! Теперь ты можешь пользоваться ботом.")
    await state.clear()

# Шаги регистрации
@router.message(Register.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Теперь введи свою фамилию:")
    await state.set_state(Register.last_name)

@router.message(Register.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Из какого ты города?")
    await state.set_state(Register.city)

@router.message(Register.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Укажи свою школу:")
    await state.set_state(Register.school)

@router.message(Register.school)
async def process_school(message: Message, state: FSMContext):
    await state.update_data(school=message.text)
    await message.answer("Теперь введи класс (например, 9):")
    await state.set_state(Register.grade)

@router.message(Register.grade)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text)
    await finish_registration(message, state)

# Проверка и запуск регистрации вручную
async def register_user_if_needed(message: Message, bot):
    user_id = str(message.from_user.id)
    if user_id in user_profiles:
        return

    await message.answer("👋 Привет! Давай сначала зарегистрируемся. Введи своё имя:")
    state = FSMContext(storage=bot.dispatcher.storage, key=message.from_user.id)
    await state.set_state(Register.first_name)
