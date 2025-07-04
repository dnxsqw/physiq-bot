import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# FSM состояния для регистрации
class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    city = State()
    school = State()
    grade = State()

# Локальная база
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# Загрузка локального словаря пользователей
with open(USERS_FILE, "r") as f:
    user_profiles = json.load(f)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
GOOGLE_JSON_KEYFILE = os.getenv("GOOGLE_CREDENTIALS_JSON")

def sync_to_google(user_id):
    if not GOOGLE_JSON_KEYFILE:
        print("GOOGLE_CREDENTIALS_JSON not set")
        return

    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON_KEYFILE), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iL29fmMyUD3htVfsXVMmwSYAnQapM4p4tMFcRntZ0vU/edit").sheet1

    user = user_profiles[str(user_id)]
    telegram = user.get("telegram_username", "")
    data = [user["first_name"], user["last_name"], user["city"], user["school_normalized"], user["grade"], telegram, user_id]

    existing = sheet.col_values(7)
    if str(user_id) in existing:
        row = existing.index(str(user_id)) + 1
        sheet.update(f"A{row}:G{row}", [data])
    else:
        sheet.append_row(data)

# Регистрация нового пользователя
async def register_user_if_needed(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if user_id not in user_profiles:
        await message.answer("Добро пожаловать! Давай создадим твой профиль.\nКак тебя зовут? (Имя)")
        await state.set_state(Registration.first_name)
    else:
        await message.answer("Ты уже зарегистрирован. Используй /profile чтобы посмотреть или изменить данные.")

# Обработка данных
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer("Фамилия?")
    await state.set_state(Registration.last_name)

async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    await message.answer("Город?")
    await state.set_state(Registration.city)

async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await message.answer("Полное название школы?")
    await state.set_state(Registration.school)

async def process_school(message: types.Message, state: FSMContext):
    school_raw = message.text.strip()
    normalized = normalize_school_name(school_raw)
    await state.update_data(school=school_raw, school_normalized=normalized)
    await message.answer("Класс?")
    await state.set_state(Registration.grade)

async def process_grade(message: types.Message, state: FSMContext):
    data = await state.get_data()
    grade = message.text.strip()
    user_id = str(message.from_user.id)

    user_profiles[user_id] = {
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "city": data["city"],
        "school": data["school"],
        "school_normalized": data["school_normalized"],
        "grade": grade,
        "telegram_username": message.from_user.username or "",
        "registered_at": datetime.now().isoformat(),
        "tasks_solved": 0,
        "manuls": 0,
        "streak": 0,
        "achievements": []
    }

    with open(USERS_FILE, "w") as f:
        json.dump(user_profiles, f, indent=2, ensure_ascii=False)

    sync_to_google(user_id)

    await message.answer("✅ Профиль создан!")
    await state.clear()

# Функция нормализации школы
def normalize_school_name(school: str) -> str:
    school = school.lower().strip()
    replacements = {
        "рфмш": "РФМШ",
        "г. астана": "Астана",
        "астана": "Астана",
        "школа-лицей": "Школа-лицей"
    }
    for k, v in replacements.items():
        school = school.replace(k, v)
    return school.title()

# Просмотр профиля
async def view_profile(message: types.Message):
    user_id = str(message.from_user.id)
    user = user_profiles.get(user_id)

    if not user:
        await message.answer("Ты ещё не зарегистрирован. Нажми /start.")
        return

    msg = (
        f"🧑‍🔬 <b>Профиль физика</b>\n"
        f"👤 {user['first_name']} {user['last_name']}\n"
        f"🏙 {user['city']}\n"
        f"🏫 {user['school_normalized']}\n"
        f"📚 Класс: {user['grade']}\n"
        f"🔥 Решено задач: {user['tasks_solved']}\n"
        f"🕊 Манулы: {user['manuls']}\n"
        f"📈 Стрик: {user['streak']} дней"
    )
    await message.answer(msg, parse_mode="HTML")
