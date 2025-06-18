import hashlib
import math
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.config import settings
from app.models.problem import Problem
from app.models.attempt import Attempt
from app.models.user import User
from app.models.prize_pool import PrizePool
from app.services.payman_service import payman_service
from app.services.problem_bank_service import problem_bank

class GameService:
    def __init__(self):
        self.BASE_COST = 0.50  
        self.ESCALATION_HOURS = 6 
        self.GOLDEN_RATIO = 1.618033988749  # φ (phi) - nature's perfect ratio
        self.E_CONSTANT = 2.71828182846  # Euler's number - compound growth
        
        self.WINNER_RATIO = 0.80
        self.ROLLOVER_RATIO = 0.20 
        self.BASE_PRIZE_POOL = 20.0
        
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
        now = datetime.utcnow()
        
        if hasattr(problem_created_at, 'tzinfo') and problem_created_at.tzinfo is not None:
            timestamp = problem_created_at.timestamp()
            problem_created_at_naive = datetime.utcfromtimestamp(timestamp)
        else:
            problem_created_at_naive = problem_created_at
        
        hours_elapsed = (now - problem_created_at_naive).total_seconds() / 3600
        escalation_periods = hours_elapsed / self.ESCALATION_HOURS
        
        golden_factor = self.GOLDEN_RATIO ** escalation_periods
        
        urgency_factor = 1 + math.e ** (hours_elapsed / 72) - 1
        
        cost = self.BASE_COST * golden_factor * (1 + urgency_factor * 0.1)
        
        return round(min(cost, 100.0), 2)
        
    def hash_answer(self, answer: str) -> str:
        """Hash an answer for secure comparison"""
        return hashlib.sha256(answer.lower().strip().encode()).hexdigest()
    
    def check_answer(self, guess: str, correct_answer_hash: str) -> bool:
        """Check if guess matches the correct answer"""
        guess_hash = self.hash_answer(guess)
        return guess_hash == correct_answer_hash
    
    async def get_current_problem(self, db: AsyncSession) -> Problem:
        """Get the current active problem"""
        result = await db.execute(select(Problem).where(Problem.is_active == True))
        return result.scalar_one_or_none()
    
    async def get_current_prize_pool(self, problem_id: int, db: AsyncSession) -> float:
        """Get current prize pool amount"""
        result = await db.execute(
            select(PrizePool).where(PrizePool.problem_id == problem_id)
        )
        prize_pool = result.scalar_one_or_none()
        return float(prize_pool.pool_amount) if prize_pool else self.BASE_PRIZE_POOL
    
    async def create_new_problem(self, db: AsyncSession, rollover_amount: float = None) -> Problem:
        """Create a new problem with rollover from previous"""
        problem_data = problem_bank.get_random_problem()
        
        new_problem = Problem(
            question=problem_data["question"],
            answer_hash=self.hash_answer(problem_data["answer"]),
            is_active=True
        )
        db.add(new_problem)
        await db.flush() 
        
        starting_amount = rollover_amount if rollover_amount else self.BASE_PRIZE_POOL
        starting_amount_decimal = Decimal(str(starting_amount))
        
        new_prize_pool = PrizePool(
            problem_id=new_problem.id,
            pool_amount=starting_amount_decimal,
            base_amount=starting_amount_decimal
        )
        db.add(new_prize_pool)
        
        await db.commit()
        await db.refresh(new_problem)
        
        return new_problem
    
    async def process_attempt(self, user: User, guess: str, db: AsyncSession) -> dict:
        """Process a user's guess attempt"""
        problem = await self.get_current_problem(db)
        if not problem:
            problem = await self.create_new_problem(db)
        
        cost = self.calculate_attempt_cost(problem.created_at)

        if not user.payman_id or not user.payman_id.startswith("wlt-"):
            balance_data = await payman_service.get_balance(user.payman_access_token)
            if balance_data.get("success") and balance_data.get("wallet_id"):
                user.payman_id = balance_data.get("wallet_id")
                await db.commit()
                print(f"✅ Updated missing wallet ID: {user.payman_id}")
            else:
                return {
                    "error": "Your wallet connection doesn't have a valid wallet ID. Please use /start to reconnect.",
                    "wallet_id_missing": True
                }
        
        charge_result = await payman_service.charge_user(
            access_token=settings.APP_PAYMAN_ACCESS_TOKEN,
            amount=cost,
            description=f"Attempt for Problem #{problem.id}",
            user_id=user.payman_id,
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
            return {"error": f"💳 Payment failed: {charge_result.get('error', 'Unknown error')}"}
        
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
            prize_pool.pool_amount += Decimal(str(cost))
        else:
            new_pool = PrizePool(
                problem_id=problem.id,
                pool_amount=Decimal(str(cost)) + Decimal(str(self.BASE_PRIZE_POOL)), 
                base_amount=Decimal(str(self.BASE_PRIZE_POOL))
            )
            db.add(new_pool)
        
        await db.commit()
        
        if is_correct:
            return await self.handle_winner(user, problem, attempt, db)
        else:
            current_pool = await self.get_current_prize_pool(problem.id, db)
            
            now = datetime.utcnow()
            
            if hasattr(problem.created_at, 'tzinfo') and problem.created_at.tzinfo is not None:
                timestamp = problem.created_at.timestamp()
                problem_time = datetime.utcfromtimestamp(timestamp)
            else:
                problem_time = problem.created_at

            hours_elapsed = (now - problem_time).total_seconds() / 3600
            
            return {
                "success": True,
                "is_correct": False,
                "cost": cost,
                "attempt_id": attempt.id,
                "current_pool": current_pool,
                "hours_elapsed": hours_elapsed
            }
    
    async def handle_winner(self, user: User, problem: Problem, attempt: Attempt, db: AsyncSession) -> dict:
        """Handle winner: payout 80%, rollover 20%, start new game"""
        current_pool = await self.get_current_prize_pool(problem.id, db)
        
        current_pool_decimal = Decimal(str(current_pool))
        winner_ratio_decimal = Decimal(str(self.WINNER_RATIO))
        rollover_ratio_decimal = Decimal(str(self.ROLLOVER_RATIO))

        winner_payout = round(current_pool_decimal * winner_ratio_decimal, 2)
        rollover_amount = round(current_pool_decimal * rollover_ratio_decimal, 2)
        
        # Convert back to float for API responses
        winner_payout_float = float(winner_payout)
        rollover_amount_float = float(rollover_amount)

        if not user.payman_id:
            return {"error": "Your wallet is connected but missing a Payman ID. Please reconnect with /start"}
        
        payout_result = await payman_service.payout_winner(
            access_token=user.payman_access_token,
            amount=winner_payout_float,
            payee_id=user.payman_payee_id,
            description=f"🏆 Prize Pool Winner - Problem #{problem.id}"
        )
        
        problem.is_active = False
        problem.ended_at = datetime.utcnow()
        
        result = await db.execute(
            select(PrizePool).where(PrizePool.problem_id == problem.id)
        )
        prize_pool = result.scalar_one_or_none()
        
        if prize_pool:
            prize_pool.winner_user_id = user.id
            prize_pool.paid_out = True
        
        new_problem = await self.create_new_problem(db, rollover_amount_float)
        
        await db.commit()
        
        return {
            "success": True,
            "is_correct": True,
            "is_winner": True,
            "cost": float(attempt.amount_charged),
            "total_pool": float(current_pool),
            "winner_payout": float(winner_payout),
            "rollover_amount": float(rollover_amount),
            "payout_result": payout_result,
            "attempt_id": attempt.id,
            "new_problem": {
                "id": new_problem.id,
                "question": new_problem.question
            }
        }

game_service = GameService()