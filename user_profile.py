\import json
import os
import re
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==== FSM состояния ====
class Register(StatesGroup):
    first_name = State()
    last_name = State()
    city = State()
    school = State()
    grade = State()

# ==== Пути и константы ====
USERS_FILE = "users.json"
GOOGLE_JSON_PATH = "GOOGLE_CREDENTIALS_JSON"
GOOGLE_SHEET_NAME = "PhysIQ Users"

router = Router()
user_profiles = {}

# ==== Загрузка данных из users.json ====
def load_users():
    global user_profiles
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            user_profiles = json.load(f)
    else:
        user_profiles = {}

# ==== Сохранение users.json ====
def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_profiles, f, indent=2, ensure_ascii=False)

# ==== Нормализация названия школы ====
def normalize_school(school_name):
    return re.sub(r"\W+", " ", school_name.strip().lower()).title()

# ==== Синхронизация с Google Sheets ====
def sync_to_google(user_id):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_PATH, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1

        user = user_profiles[str(user_id)]
        rows = sheet.get_all_records()
        existing_row = next((i for i, row in enumerate(rows, start=2) if str(row.get("telegram_username")) == str(user.get("username"))), None)

        data = [
            user["username"],
            user["first_name"],
            user["last_name"],
            user["city"],
            user["school"],
            user["normalized_school"],
            user["class"],
            user["solved"],
            user["manuls"],
            user["streak"],
            ", ".join(user.get("achievements", [])),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]

        if existing_row:
            sheet.update(f"A{existing_row}:L{existing_row}", [data])
        else:
            sheet.append_row(data)
    except Exception as e:
        print("[Google Sync Error] ❌", e)

# ==== Команда /start ====
@router.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    username = message.from_user.username

    if user_id in user_profiles:
        await message.answer(f"👤 Добро пожаловать обратно, {user_profiles[user_id]['first_name']}!\n\n🧪 Вы уже зарегистрированы.")
        return

    user_profiles[user_id] = {
        "username": username,
        "first_name": "",
        "last_name": "",
        "city": "",
        "school": "",
        "normalized_school": "",
        "class": "",
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }

    await state.set_state(Register.first_name)
    await message.answer("👤 Введите ваше *имя*:")

# ==== FSM Шаги регистрации ====
@router.message(Register.first_name)
async def reg_first_name(message: types.Message, state: FSMContext):
    user_profiles[str(message.from_user.id)]["first_name"] = message.text.strip()
    await state.set_state(Register.last_name)
    await message.answer("👤 Теперь введите вашу *фамилию*:")

@router.message(Register.last_name)
async def reg_last_name(message: types.Message, state: FSMContext):
    user_profiles[str(message.from_user.id)]["last_name"] = message.text.strip()
    await state.set_state(Register.city)
    await message.answer("🏙 Введите ваш *город*:")

@router.message(Register.city)
async def reg_city(message: types.Message, state: FSMContext):
    user_profiles[str(message.from_user.id)]["city"] = message.text.strip()
    await state.set_state(Register.school)
    await message.answer("🏫 Введите полное название вашей *школы*:")

@router.message(Register.school)
async def reg_school(message: types.Message, state: FSMContext):
    school = message.text.strip()
    user_profiles[str(message.from_user.id)]["school"] = school
    user_profiles[str(message.from_user.id)]["normalized_school"] = normalize_school(school)
    await state.set_state(Register.grade)
    await message.answer("🎓 Введите ваш *класс* (например, 9):")

@router.message(Register.grade)
async def reg_grade(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_profiles[user_id]["class"] = message.text.strip()
    save_users()
    sync_to_google(user_id)
    await state.clear()

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📄 Мой профиль"), KeyboardButton(text="⚙️ Изменить профиль")]
    ], resize_keyboard=True)

    await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=kb)
