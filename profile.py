from aiogram import types, Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import json, os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

router = Router()

USERS_FILE = "users.json"
GOOGLE_SHEET_NAME = "PhysIQ Users"
GOOGLE_JSON_KEYFILE = "physiq-bot-bb4835247b64.json"

user_profiles = {}

# Загрузка
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        user_profiles = json.load(f)

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_profiles, f, indent=2, ensure_ascii=False)

def sync_to_google(user_id):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_KEYFILE, scope)
    gc = gspread.authorize(creds)
    sheet = gc.open(GOOGLE_SHEET_NAME).sheet1

    profile = user_profiles[user_id]
    values = [
        user_id,
        profile.get("username", ""),
        profile.get("first_name", ""),
        profile.get("last_name", ""),
        profile.get("city", ""),
        profile.get("school", ""),
        profile.get("normalized_school", ""),
        profile.get("class", ""),
        profile.get("manuls", 0),
        profile.get("streak", 0),
        profile.get("solved", 0),
        ",".join(profile.get("achievements", []))
    ]

    try:
        existing_ids = sheet.col_values(1)
        if user_id in existing_ids:
            row_index = existing_ids.index(user_id) + 1
            sheet.update(f"A{row_index}:L{row_index}", [values])
        else:
            sheet.append_row(values)
    except Exception as e:
        print(f"[Google Sync Error] {e}")

def normalize_school(name):
    name = name.lower()
    if "рфмш" in name and "астана" in name:
        return "РФМШ Астана"
    elif "школа-лицей" in name and "8" in name and "павлодар" in name:
        return "ШЛ №8 Павлодар"
    return name.title()

# 👤 Состояния FSM
class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    city = State()
    school = State()
    class_num = State()

@router.message(F.text == "📋 Зарегистрироваться")
async def begin_registration(message: types.Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(Registration.first_name)

@router.message(Registration.first_name)
async def process_first(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(Registration.last_name)

@router.message(Registration.last_name)
async def process_last(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Введите ваш город:")
    await state.set_state(Registration.city)

@router.message(Registration.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Введите вашу школу (полное название):")
    await state.set_state(Registration.school)

@router.message(Registration.school)
async def process_school(message: types.Message, state: FSMContext):
    await state.update_data(school=message.text)
    await message.answer("Введите ваш класс:")
    await state.set_state(Registration.class_num)
@router.message(Registration.class_num)
async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""
    normalized = normalize_school(data["school"])

    user_profiles[user_id] = {
        "username": username,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "city": data["city"],
        "school": data["school"],
        "normalized_school": normalized,
        "class": message.text,
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }

    # 🔎 ЛОГ
    print(f"[DEBUG] Новый профиль создан: {user_profiles[user_id]}")

    try:
        save_users()
        print("[DEBUG] ✅ Профиль сохранён в users.json")
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка сохранения JSON: {e}")

    try:
        sync_to_google(user_id)
        print("[DEBUG] ✅ Синхронизация с Google Таблицей успешна")
    except Exception as e:
        print(f"[Google Sync Error] ❌ {e}")

    await message.answer("✅ Вы успешно зарегистрированы!")
    await state.clear()
