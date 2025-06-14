from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ClientBase(BaseModel):
    last_name: str
    first_name: Optional[str] = ""
    middle_name: Optional[str] = ""
    purchased_sessions: int = 0
    subscription_end: Optional[datetime] = None
    telegram: Optional[str] = ""
    comment: Optional[str] = ""
    unlimited: bool = False

class ClientCreate(ClientBase):
    pass

class ClientRead(ClientBase):
    id: int

    class Config:
        orm_mode = True

class PurchaseBase(BaseModel):
    name: str
    sessions_count: int
    unlimited: bool
    duration_months: int
    cost: float

class PurchaseCreate(PurchaseBase):
    pass

class PurchaseRead(PurchaseBase):
    id: int

    class Config:
        orm_mode = True
