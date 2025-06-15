import hashlib
import math
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.problem import Problem
from app.models.attempt import Attempt
from app.models.user import User
from app.models.prize_pool import PrizePool
from app.services.payman_service import payman_service

class GameService:
    def __init__(self):
        self.BASE_COST = 0.50  
        self.ESCALATION_HOURS = 6 
        self.GOLDEN_RATIO = 1.618033988749  # φ (phi) - nature's perfect ratio
        self.E_CONSTANT = 2.71828182846  # Euler's number - compound growth
        
        self.WINNER_RATIO = 0.80
        self.ROLLOVER_RATIO = 0.20 
        
    def calculate_attempt_cost(self, problem_created_at: datetime) -> float:
        """
        Mathematical cost escalation using Golden Ratio and Exponential Growth
        
        Philosophy:
        - Golden Ratio (φ): Found in nature, represents perfect balance and growth
        - Exponential factor: Mirrors real market dynamics and urgency
        - Fibonacci-like progression: Creates natural, predictable scaling
        
        Formula: cost = base * φ^(hours/6) * (1 + e^(hours/72))
        
        This creates:
        - Hour 0-6: $0.50 - $0.81 (accessible entry)
        - Hour 6-12: $0.81 - $1.31 (moderate commitment)  
        - Hour 12-18: $1.31 - $2.12 (serious players)
        - Hour 18-24: $2.12 - $3.43 (high stakes)
        - Hour 24+: Exponential growth (creates urgency)
        """
        hours_elapsed = (datetime.utcnow() - problem_created_at).total_seconds() / 3600
        escalation_periods = hours_elapsed / self.ESCALATION_HOURS
        
        golden_factor = self.GOLDEN_RATIO ** escalation_periods
        
        urgency_factor = 1 + (math.e ** (hours_elapsed / 72) - 1) * 0.1

        fibonacci_factor = 1 + (escalation_periods * 0.1)
        
        cost = self.BASE_COST * golden_factor * urgency_factor * fibonacci_factor
        
        return min(cost, 100.0)
    
    async def get_current_problem(self, db: AsyncSession) -> Problem:
        """Get the current active problem"""
        result = await db.execute(select(Problem).where(Problem.is_active == True))
        return result.scalar_one_or_none()
    
    def hash_answer(self, answer: str) -> str:
        """Hash an answer for comparison"""
        return hashlib.sha256(answer.lower().strip().encode()).hexdigest()
    
    def check_answer(self, guess: str, correct_answer_hash: str) -> bool:
        """Check if guess matches the correct answer"""
        guess_hash = self.hash_answer(guess)
        return guess_hash == correct_answer_hash
    
    async def get_current_prize_pool(self, problem_id: int, db: AsyncSession) -> float:
        """Get current prize pool amount"""
        result = await db.execute(
            select(PrizePool).where(PrizePool.problem_id == problem_id)
        )
        prize_pool = result.scalar_one_or_none()
        return float(prize_pool.pool_amount) if prize_pool else 20.0
    
    async def calculate_winner_payout(self, total_pool: float) -> tuple[float, float]:
        """Calculate winner payout (80%) and rollover (20%)"""
        winner_amount = total_pool * self.WINNER_RATIO
        rollover_amount = total_pool * self.ROLLOVER_RATIO
        return winner_amount, rollover_amount
    

    async def process_attempt(self, user: User, guess: str, db: AsyncSession) -> dict:
        """Process a user's guess attempt with token expiration handling"""
        problem = await self.get_current_problem(db)
        if not problem:
            return {"error": "No active problem"}
        
        cost = self.calculate_attempt_cost(problem.created_at)
        
        charge_result = await payman_service.charge_user(
            access_token=user.payman_access_token,
            amount=cost,
            description=f"Attempt for Problem #{problem.id} - Escalated Cost",
            user_id=user.payman_id
        )
        
        if charge_result.get("error") == "TOKEN_EXPIRED":
            user.payman_access_token = None
            user.payman_id = None
            await db.commit()
            
            return {
                "error": "🔄 Your wallet connection has expired. Please use /start to reconnect your Payman wallet.",
                "token_expired": True
            }
        
        if not charge_result.get("success"):
            return {"error": "Payment failed", "details": charge_result.get("error", "Unknown error")}
        
        is_correct = self.check_answer(guess, problem.answer_hash)
        
        attempt = Attempt(
            user_id=user.id,
            problem_id=problem.id,
            guess=guess,
            is_correct=is_correct,
            amount_charged=cost
        )
        db.add(attempt)
        
        result = await db.execute(
            select(PrizePool).where(PrizePool.problem_id == problem.id)
        )
        prize_pool = result.scalar_one_or_none()
        if prize_pool:
            prize_pool.pool_amount += cost
        else:
            new_pool = PrizePool(
                problem_id=problem.id,
                pool_amount=cost + 20.0, 
                base_amount=20.0
            )
            db.add(new_pool)
        
        await db.commit()
        
        if is_correct:
            return await self.handle_winner(user, problem, attempt, db)
        
        return {
            "success": True,
            "is_correct": False,
            "cost": cost,
            "attempt_id": attempt.id,
            "current_pool": await self.get_current_prize_pool(problem.id, db),
            "hours_elapsed": (datetime.utcnow() - problem.created_at).total_seconds() / 3600
        }
    
    async def handle_winner(self, user: User, problem: Problem, attempt: Attempt, db: AsyncSession) -> dict:
        """Handle winner: payout 80%, rollover 20%, start new game"""
        current_pool = await self.get_current_prize_pool(problem.id, db)
        winner_payout, rollover_amount = await self.calculate_winner_payout(current_pool)
        
        payout_result = await payman_service.payout_winner(
            access_token=user.payman_access_token,
            amount=winner_payout,
            user_id=user.payman_id,
            description=f"🏆 Prize Pool Winner - Problem #{problem.id} - {winner_payout:.2f}"
        )
        
        problem.is_active = False
        problem.ended_at = datetime.utcnow()
        problem.winner_user_id = user.id
        
        await self.create_next_problem(rollover_amount, db)
        
        await db.commit()
        
        return {
            "success": True,
            "is_correct": True,
            "is_winner": True,
            "cost": attempt.amount_charged,
            "total_pool": current_pool,
            "winner_payout": winner_payout,
            "rollover_amount": rollover_amount,
            "payout_result": payout_result,
            "attempt_id": attempt.id
        }
    
    async def create_next_problem(self, rollover_amount: float, db: AsyncSession):
        """Create the next problem with rollover amount as base"""
        sample_problems = [
            {"question": "I speak without a mouth and hear without ears. What am I?", "answer": "echo"},
            {"question": "What has keys but no locks, space but no room?", "answer": "keyboard"},
            {"question": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
            {"question": "What can travel around the world while staying in a corner?", "answer": "stamp"},
            {"question": "What gets sharper the more you use it?", "answer": "brain"}
        ]
        
        import random
        chosen = random.choice(sample_problems)
        answer_hash = self.hash_answer(chosen["answer"])
        
        new_problem = Problem(
            question=chosen["question"],
            answer_hash=answer_hash,
            is_active=True
        )
        db.add(new_problem)
        await db.flush()
        
        new_prize_pool = PrizePool(
            problem_id=new_problem.id,
            pool_amount=rollover_amount,
            base_amount=rollover_amount
        )
        db.add(new_prize_pool)
        
        print(f"🎯 New problem created: {chosen['question']}")
        print(f"💰 Starting pool: ${rollover_amount:.2f}")

game_service = GameService()