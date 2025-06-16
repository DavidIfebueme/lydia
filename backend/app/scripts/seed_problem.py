# scripts/seed_problem.py
import asyncio
import hashlib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models.problem import Problem
from app.models.prize_pool import PrizePool

async def create_initial_problem():
    async with AsyncSessionLocal() as db:
        # Check if problem already exists
        from sqlalchemy import select
        result = await db.execute(select(Problem))
        if result.scalars().first():
            print("❌ Problem already exists, skipping...")
            return
        
        # Create first problem
        answer = "173"
        answer_hash = hashlib.sha256(answer.lower().strip().encode()).hexdigest()
        
        problem = Problem(
            question="I'm thinking of a random number betweeen 1 and 200. what is it?",
            answer_hash=answer_hash,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(problem)
        await db.flush()
        
        # Create initial prize pool (starts with $20 base)
        prize_pool = PrizePool(
            problem_id=problem.id,
            pool_amount=20.0,
            base_amount=20.0
        )
        db.add(prize_pool)
        
        await db.commit()
        print(f"✅ Created problem: {problem.question}")
        print(f"✅ Answer: {answer} (hash: {answer_hash[:8]}...)")
        print(f"✅ Starting pool: $20.00")

if __name__ == "__main__":
    asyncio.run(create_initial_problem())