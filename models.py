from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Client(BaseModel):
    id: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = ""
    purchased_sessions: int
    subscription_end: datetime
    telegram: Optional[str] = ""
    comment: Optional[str] = ""
    unlimited: bool
    phone: Optional[str] = ""
