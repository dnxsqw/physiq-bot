import json, os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import types

USERS_FILE = "users.json"
GOOGLE_SHEET_NAME = "PhysIQ Users"
GOOGLE_JSON_KEYFILE = "physiq-bot-bb4835247b64.json"

user_profiles = {}

# Загрузка пользователей
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

async def register_user_if_needed(message: types.Message, bot):
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""
    await message.answer("Введите ваше имя:")
    first = await bot.wait_for("message")
    await message.answer("Введите вашу фамилию:")
    last = await bot.wait_for("message")
    await message.answer("Введите ваш город:")
    city = await bot.wait_for("message")
    await message.answer("Введите вашу школу (полное название):")
    school = await bot.wait_for("message")
    await message.answer("Введите ваш класс (например, 9):")
    class_resp = await bot.wait_for("message")

    normalized = normalize_school(school.text)

    user_profiles[user_id] = {
        "username": username,
        "first_name": first.text,
        "last_name": last.text,
        "city": city.text,
        "school": school.text,
        "normalized_school": normalized,
        "class": class_resp.text,
        "manuls": 0,
        "streak": 0,
        "solved": 0,
        "achievements": []
    }
    save_users()
    sync_to_google(user_id)
    await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=main_menu)

def normalize_school(name):
    name = name.lower()
    if "рфмш" in name and "астана" in name:
        return "РФМШ Астана"
    elif "школа-лицей" in name and "8" in name and "павлодар" in name:
        return "ШЛ №8 Павлодар"
    return name.title()
