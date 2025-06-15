# api_server.py

from fastapi import FastAPI
from typing import List
from models import Client
import data_store

app = FastAPI()

@app.post("/upload/clients")
def upload_clients(clients: List[Client]):
    data_store.load_clients(clients)
    return {"status": "ok", "count": len(clients)}

@app.get("/clients/by_last_name")
def get_by_last_name(last_name: str):
    return data_store.find_clients_by_last_name(last_name)

@app.get("/clients/by_phone")
def get_by_phone(phone: str):
    return data_store.find_clients_by_phone(phone)


