from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.user import Base 

class PrizePool(Base):
    __tablename__ = "prize_pools"    
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    pool_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    base_amount = Column(Numeric(10, 2), nullable=False, default=20.0)
    winner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_out = Column(Boolean, default=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())