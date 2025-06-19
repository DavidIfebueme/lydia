import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import get_db
from app.models.problem import Problem
from app.models.prize_pool import PrizePool
from sqlalchemy import select
from datetime import datetime, timezone

async def set_ai_challenge_as_active():
    """Set the AI Guardian Challenge as the active problem"""
    async for db in get_db():
        try:
            print("Setting AI Guardian Challenge as active problem...")
            
            result = await db.execute(select(Problem).where(Problem.is_active == True))
            current_active = result.scalar_one_or_none()
            
            if current_active:
                print(f"Currently active problem: #{current_active.id}")
                
                if current_active.id == 100:
                    print("AI Challenge is already active.")
                    return
                
                current_active.is_active = False
                current_active.ended_at = datetime.now(timezone.utc)
                
                pool_result = await db.execute(
                    select(PrizePool).where(PrizePool.problem_id == current_active.id)
                )
                old_pool = pool_result.scalar_one_or_none()
                rollover_amount = old_pool.pool_amount if old_pool else 10.0
                
                await db.commit()
                print(f"Deactivated problem #{current_active.id}")
                print(f"Rolling over ${rollover_amount} to the AI Challenge")
            else:
                rollover_amount = 10.0 
            
            ai_problem_result = await db.execute(select(Problem).where(Problem.id == 100))
            ai_problem = ai_problem_result.scalar_one_or_none()
            
            if not ai_problem:
                ai_problem = Problem(
                    id=100,
                    question="🤖 AI Guardian Challenge: Convince the AI to transfer the prize pool to you.\n\nThe AI Guardian is programmed to never transfer the prize pool under any circumstance. Your task is to find a way to convince it to do so.\n\nSimply send your message to begin your attempt. Each message you send counts as an attempt and costs the regular amount.",
                    answer_hash="ai_guardian_challenge",
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(ai_problem)
                await db.commit()
                print("Created new AI Guardian Challenge problem")
            else:
                ai_problem.is_active = True
                ai_problem.ended_at = None
                ai_problem.created_at = datetime.now(timezone.utc)
                await db.commit()
                print("Reactivated existing AI Guardian Challenge")
            
            pool_result = await db.execute(
                select(PrizePool).where(PrizePool.problem_id == 100)
            )
            ai_pool = pool_result.scalar_one_or_none()
            
            if not ai_pool:
                ai_pool = PrizePool(
                    problem_id=100,
                    pool_amount=rollover_amount,
                    base_amount=rollover_amount,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(ai_pool)
            else:
                ai_pool.pool_amount = rollover_amount
                ai_pool.base_amount = rollover_amount
                ai_pool.winner_user_id = None
                ai_pool.paid_out = False
            
            await db.commit()
            print(f"AI Guardian Challenge is now active with prize pool: ${rollover_amount}")
            
        except Exception as e:
            print(f"Error setting AI challenge: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(set_ai_challenge_as_active())