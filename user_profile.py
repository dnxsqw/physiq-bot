import json
import os
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from oauth2client.service_account import ServiceAccountCredentials
import gspread

router = Router()

USERS_FILE = "users.json"
GOOGLE_JSON_KEYFILE = "physiq-bot-bb4835247b64.json"
GOOGLE_SHEET_NAME = "PhysIQ Users"

# FSM-состояния для регистрации
class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    city = State()
    school = State()
    class_num = State()

# Загрузка профилей
def load_profiles():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Сохранение профилей
def save_profiles(profiles):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

# Нормализация школ
def normalize_school_name(name: str) -> str:
    name = name.lower()
    name = name.replace("рфмш", "рфмш").replace("г.", "").replace("город", "")
    name = name.replace("астана", "астана").replace("нур-султан", "астана")
    return name.strip().title()

# Загрузка/создание профиля
user_profiles = load_profiles()

# Команда: регистрация
@router.message(F.text.lower() == "зарегистрироваться")
async def start_registration(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введи своё **имя**:")
    await state.set_state(Registration.first_name)

@router.message(Registration.first_name)
async def reg_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Теперь фамилию:")
    await state.set_state(Registration.last_name)

@router.message(Registration.last_name)
async def reg_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Твой город:")
    await state.set_state(Registration.city)

@router.message(Registration.city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Полное название школы:")
    await state.set_state(Registration.school)

@router.message(Registration.school)
async def reg_school(message: types.Message, state: FSMContext):
    await state.update_data(school=message.text)
    await message.answer("Класс:")
    await state.set_state(Registration.class_num)

@router.message(Registration.class_num)
async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = str(message.from_user.id)
    username = message.from_user.username or "—"

    profile = {
        "username": username,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "city": data["city"],
        "school": data["school"],
        "normalized_school": normalize_school_name(data["school"]),
        "class": data["class_num"],
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }

    user_profiles[user_id] = profile
    save_profiles(user_profiles)
    print(f"[DEBUG] Новый профиль создан: {profile}")

    try:
        sync_to_google(user_id)
        print("[Google Sync] ✅ Синхронизировано")
    except Exception as e:
        print(f"[Google Sync Error] ❌ {e}")

    await message.answer("✅ Регистрация завершена! Напиши «Мой профиль», чтобы посмотреть его.")
    await state.clear()

# Команда: мой профиль
@router.message(F.text.lower() == "мой профиль")
async def show_profile(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_profiles:
        await message.answer("🔹 Сначала нужно зарегистрироваться — нажми кнопку «Зарегистрироваться»!")
        return

    p = user_profiles[user_id]
    profile_text = (
        f"👤 <b>{p['first_name']} {p['last_name']}</b>\n"
        f"🏙️ <b>Город:</b> {p['city']}\n"
        f"🏫 <b>Школа:</b> {p['school']}\n"
        f"🎓 <b>Класс:</b> {p['class']}\n"
        f"\n📈 <b>Решено задач:</b> {p['solved']}\n"
        f"🔥 <b>Стрик:</b> {p['streak']}\n"
        f"🦊 <b>Манулы:</b> {p['manuls']}"
    )
    await message.answer(profile_text, parse_mode="HTML")

# Функция синхронизации с Google Таблицей
def sync_to_google(user_id):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_KEYFILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1

    user = user_profiles[user_id]
    username = user.get("username", "—")
    normalized_school = user.get("normalized_school", "")

    # Проверка, есть ли пользователь
    existing = sheet.findall(str(user_id))
    if not existing:
        row = [
            user_id,
            username,
            user["first_name"],
            user["last_name"],
            user["city"],
            user["school"],
            normalized_school,
            user["class"],
            user["manuls"],
            user["streak"],
            user["solved"]
        ]
        sheet.append_row(row)
