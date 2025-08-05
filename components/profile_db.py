import json
import os

PROFILE_DB_PATH = "data/profiles.json"  # путь к файлу профилей, поправь под себя

def _load_profiles():
    """Загрузить все профили из файла."""
    if not os.path.exists(PROFILE_DB_PATH):
        return {}
    with open(PROFILE_DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def _save_profiles(profiles):
    """Сохранить все профили в файл."""
    with open(PROFILE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def save_user_name(chat_id, name):
    """Сохранить имя пользователя."""
    profiles = _load_profiles()
    profiles[str(chat_id)] = profiles.get(str(chat_id), {})
    profiles[str(chat_id)]["name"] = name
    _save_profiles(profiles)

def get_user_name(chat_id):
    """Получить имя пользователя."""
    profiles = _load_profiles()
    return profiles.get(str(chat_id), {}).get("name", None)
