from typing import List
from models import Client

clients: List[Client] = []

def load_clients(new_clients: List[Client]):
    global clients
    clients = new_clients

def find_clients_by_last_name(last_name: str) -> List[Client]:
    return [c for c in clients if c.last_name.lower() == last_name.lower()]

def find_clients_by_phone(phone: str) -> List[Client]:
    return [c for c in clients if c.phone and c.phone == phone]


