from typing import List, Dict
from models import Client
import json
import os
from utils_yadisk import download_file_yadisk, upload_file_yadisk

clients: List[Client] = []
auth_users: Dict[int, Dict] = {}

TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

AUTH_USERS_PATH = os.path.join(TMP_DIR, "auth_users.json")
CLIENTS_PATH = os.path.join(TMP_DIR, "clients.json")

def save_auth_users():
    with open(AUTH_USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(auth_users, f, indent=2, ensure_ascii=False)
    upload_file_yadisk(AUTH_USERS_PATH, "/titanbot/auth_users.json")

def restore_auth_users():
    if download_file_yadisk("/titanbot/auth_users.json", AUTH_USERS_PATH):
        try:
            with open(AUTH_USERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                auth_users.clear()
                auth_users.update({int(k): v for k, v in data.items()})
            print(f"✅ Восстановлено авторизованных пользователей: {len(auth_users)}")
        except Exception as e:
            print(f"❌ Ошибка при чтении auth_users.json: {e}")

def add_authorized_user(chat_id: int, last_name: str, phone: str = ""):
    auth_users[chat_id] = {"last_name": last_name, "phone": phone}
    save_auth_users()

def remove_authorized_user(chat_id: int):
    if chat_id in auth_users:
        del auth_users[chat_id]
        save_auth_users()

def is_user_authorized(chat_id: int) -> bool:
    return chat_id in auth_users

def get_user_info(chat_id: int) -> Dict:
    return auth_users.get(chat_id, {})

def load_clients(new_clients: List[Client]):
    global clients
    clients = new_clients
    save_clients()

def save_clients():
    def serialize_client(c: Client):
        data = c.model_dump(by_alias=True)
        if c.subscription_end:
            data["SubscriptionEnd"] = c.subscription_end.isoformat()
        return data

    with open(CLIENTS_PATH, "w", encoding="utf-8") as f:
        json.dump([serialize_client(c) for c in clients], f, indent=2, ensure_ascii=False)

    upload_file_yadisk(CLIENTS_PATH, "/titanbot/clients.json")

def restore_clients_from_file():
    if download_file_yadisk("/titanbot/clients.json", CLIENTS_PATH):
        try:
            with open(CLIENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                global clients
                clients = [Client(**c) for c in data]
            print(f"✅ Восстановлено клиентов: {len(clients)}")
        except Exception as e:
            print(f"❌ Ошибка при чтении clients.json: {e}")

def find_client_by_last_name_and_phone(last_name: str, phone: str) -> Client | None:
    last = last_name.strip().lower()
    phone = phone.strip()
    for client in clients:
        if client.last_name.strip().lower() == last:
            if not phone or phone == client.phone:
                return client
    return None
