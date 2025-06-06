from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProblemBase(BaseModel):
    question: str

class ProblemCreate(ProblemBase):
    answer_hash: str

class Problem(ProblemBase):
    id: int
    answer_hash: str
    is_active: bool
    created_at: datetime
    ended_at: Optional[datetime]

    class Config:
        orm_mode = True