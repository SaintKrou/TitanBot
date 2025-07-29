import json
import os
import logging
from models import Client
from utils_yadisk import upload_file_yadisk

clients = []
auth_users = {}

CLIENTS_FILE = "clients.json"
AUTH_USERS_FILE = "auth_users.json"
CLIENTS_REMOTE_FILE = "/titanbot/clients.json"
AUTH_USERS_REMOTE_FILE = "/titanbot/auth_users.json"


def restore_clients_from_file():
    global clients
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
            clients_data = json.load(f)
            clients = [Client(**client) for client in clients_data]
        logging.info(f"✅ Загружено клиентов: {len(clients)}")
    else:
        logging.warning("⚠️ Файл clients.json не найден")


def restore_auth_users():
    global auth_users
    if os.path.exists(AUTH_USERS_FILE):
        with open(AUTH_USERS_FILE, "r", encoding="utf-8") as f:
            auth_users.update(json.load(f))
        logging.info(f"✅ Загружено авторизованных пользователей: {len(auth_users)}")
    else:
        logging.warning("⚠️ Файл auth_users.json не найден")


def save_auth_users():
    with open(AUTH_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_users, f, ensure_ascii=False, indent=2)

    try:
        upload_file_yadisk(AUTH_USERS_FILE, AUTH_USERS_REMOTE_FILE)
        logging.info("✅ auth_users.json загружен на Яндекс.Диск")
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке auth_users.json на Яндекс.Диск: {e}")


def is_user_authorized(chat_id: int) -> bool:
    return str(chat_id) in auth_users


def add_authorized_user(chat_id: int, last_name: str, phone: str = ""):
    auth_users[str(chat_id)] = {"last_name": last_name, "phone": phone.strip()}
    save_auth_users()


def remove_authorized_user(chat_id: int):
    if str(chat_id) in auth_users:
        del auth_users[str(chat_id)]
        save_auth_users()


def get_user_info(chat_id: int) -> dict:
    return auth_users.get(str(chat_id), {})


def find_clients_by_exact_last_name(last_name: str) -> list[Client]:
    return [c for c in clients if c.last_name.lower() == last_name.lower()]


def find_client_by_last_name_and_phone(last_name: str, phone: str) -> Client | None:
    phone = phone.strip()
    for client in clients:
        if client.last_name.lower() == last_name.lower() and (client.phone or "").strip() == phone:
            return client
    return None
