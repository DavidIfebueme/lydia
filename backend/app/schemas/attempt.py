from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AttemptBase(BaseModel):
    guess: str
    amount_charged: float

class AttemptCreate(AttemptBase):
    user_id: int
    problem_id: int

class Attempt(AttemptBase):
    id: int
    user_id: int
    problem_id: int
    is_correct: bool
    created_at: datetime

    class Config:
        orm_mode = True