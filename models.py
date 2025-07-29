from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class Client(BaseModel):
    id: int = Field(alias="Id")
    last_name: str = Field(alias="LastName")
    first_name: Optional[str] = Field(default="", alias="FirstName")
    middle_name: Optional[str] = Field(default="", alias="MiddleName")
    purchased_sessions: int = Field(alias="PurchasedSessions")
    subscription_end: Optional[datetime] = Field(default=None, alias="SubscriptionEnd")
    telegram: Optional[str] = Field(default="", alias="Telegram")
    comment: Optional[str] = Field(default="", alias="Comment")
    unlimited: bool = Field(alias="Unlimited")
    phone: Optional[str] = ""

    @validator("subscription_end", pre=True)
    def parse_subscription_end(cls, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return value

class Purchase(BaseModel):
    id: int
    name: str
    sessions_count: int
    unlimited: bool
    duration_months: int
    cost: float
