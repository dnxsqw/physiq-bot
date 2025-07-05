import json
import os
import logging
from aiogram import Router, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from oauth2client.service_account import ServiceAccountCredentials
import gspread

from menu import main_menu

router = Router()

USERS_FILE = "users.json"
GOOGLE_JSON_KEYFILE = "physiq-bot-bb4835247b64.json"

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        user_profiles = json.load(f)
else:
    user_profiles = {}

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
    except Exception as e:
        logging.warning(f"[Google Sync Error] ❌ {e}")

@router.message(F.text == "📋 Зарегистрироваться")
async def start_registration(message: Message, state: FSMContext):
    await message.answer("Введи своё имя:")
    await state.set_state(Register.first_name)

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
async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = str(message.from_user.id)

    profile = {
        "username": message.from_user.username or "",
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "city": data.get("city", ""),
        "school": data.get("school", ""),
        "normalized_school": normalize_school(data.get("school", "")),
        "class": message.text.strip(),
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }
    user_profiles[user_id] = profile
    save_profiles()
    sync_to_google(user_id)

    await message.answer("🎉 Регистрация завершена!", reply_markup=main_menu)
    await state.clear()

@router.message(F.text == "📊 Мой профиль")
async def show_profile(message: Message):
    user_id = str(message.from_user.id)
    profile = user_profiles.get(user_id)

    if not profile:
        await message.answer("Ты ещё не зарегистрирован! Нажми /start.")
        return

    profile_text = (
        f"<b>👤 Профиль:</b>\n"
        f"Имя: {profile['first_name']} {profile['last_name']}\n"
        f"Город: {profile['city']}\n"
        f"Школа: {profile['school']}\n"
        f"Класс: {profile['class']}\n"
        f"Манулы: {profile['manuls']}\n"
        f"Решено задач: {profile['solved']}\n"
        f"Ачивки: {', '.join(profile['achievements']) or 'пока нет'}"
    )

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Изменить профиль"), KeyboardButton(text="🗑️ Удалить профиль")],
            [KeyboardButton(text="⬅️ В меню")]
        ],
        resize_keyboard=True
    )

    await message.answer(profile_text, reply_markup=kb)

@router.message(F.text == "⬅️ В меню")
async def back_to_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu)

@router.message(F.text == "🗑️ Удалить профиль")
async def delete_profile(message: Message):
    user_id = str(message.from_user.id)
    user_profiles.pop(user_id, None)
    save_profiles()
    await message.answer("Твой профиль удалён. Нажми /start, чтобы начать заново.")

@router.message(F.text == "✏️ Изменить профиль")
async def edit_profile(message: Message, state: FSMContext):
    await message.answer("Введи своё имя заново:")
    await state.set_state(Register.first_name)
