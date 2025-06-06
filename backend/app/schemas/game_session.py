from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GameSessionBase(BaseModel):
    problem_id: int

class GameSessionCreate(GameSessionBase):
    pass

class GameSession(GameSessionBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    winner_user_id: Optional[int]
    status: str

    class Config:
        orm_mode = True