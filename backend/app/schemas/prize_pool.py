from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PrizePoolBase(BaseModel):
    problem_id: int
    pool_amount: float
    base_amount: float

class PrizePoolCreate(PrizePoolBase):
    pass

class PrizePool(PrizePoolBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True