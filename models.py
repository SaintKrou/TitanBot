# models.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Client(BaseModel):
    id: int
    last_name: str
    first_name: Optional[str] = ""
    middle_name: Optional[str] = ""
    purchased_sessions: int
    subscription_end: Optional[datetime] = None
    telegram: Optional[str] = ""
    comment: Optional[str] = ""
    unlimited: bool = False
    phone: Optional[str] = ""

class Purchase(BaseModel):
    id: int
    name: str
    sessions_count: int
    unlimited: bool
    duration_months: int
    cost: float

