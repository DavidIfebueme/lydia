from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    payman_id: Optional[str]
    payman_access_token: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True