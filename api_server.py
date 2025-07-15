# api_server.py

from fastapi import FastAPI
from typing import List
from models import Client
import data_store
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

@app.post("/upload/clients")
def upload_clients(clients: List[Client]):
    data_store.load_clients(clients)

    # Отправка файла менеджеру
    if os.path.exists(data_store.CLIENTS_FILE):
        with open(data_store.CLIENTS_FILE, "rb") as f:
            files = {"document": (data_store.CLIENTS_FILE, f)}
            data = {"chat_id": MANAGER_CHAT_ID}
            try:
                requests.post(API_URL, data=data, files=files)
            except Exception as e:
                print(f"Ошибка отправки файла: {e}")

    return {"status": "ok", "count": len(clients)}

@app.get("/clients/by_last_name")
def get_by_last_name(last_name: str):
    return data_store.find_clients_by_last_name(last_name)

@app.get("/clients/by_phone")
def get_by_phone(phone: str):
    return data_store.find_clients_by_phone(phone)
