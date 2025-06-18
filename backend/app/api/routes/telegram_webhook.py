from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.telegram_service import telegram_service
from app.services.payman_service import payman_service
from app.services.game_service import game_service
from app.models.user import User
from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.prize_pool import PrizePool
from app.config import settings
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
import json
import re

router = APIRouter()

@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Telegram updates"""
    try:
        update = await request.json()

        if 'callback_query' in update:
            await handle_callback_query(update['callback_query'], db)
            return {"status": "ok"}
        
        parsed_message = telegram_service.parse_message(update)
        
        if not parsed_message:
            return {"status": "ok"}
        
        chat_id = parsed_message["chat_id"]
        user_id = parsed_message["user_id"]
        text = parsed_message["text"]
        username = parsed_message.get("username")
        first_name = parsed_message.get("first_name")
        
        result = await db.execute(select(User).where(User.telegram_id == str(user_id)))
        user = result.scalar_one_or_none()
        
        if text.startswith("/start"):
            await handle_start_command(chat_id, user, db, username, first_name, user_id)
        elif text.startswith("/help"):
            await handle_help_command(chat_id)
        elif text.startswith("/problem"):
            await handle_problem_command(chat_id, user, db)
        elif text.startswith("/balance"):
            await handle_balance_command(chat_id, user, db)
        elif text.startswith("/menu") or text.startswith("/commands"):
            await handle_menu_command(chat_id)
        else:
            await handle_guess_attempt(chat_id, user, text, db)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error"}
    
async def handle_menu_command(chat_id: int):
    """Display available commands as buttons"""
    await telegram_service.send_commands_menu(chat_id)


async def handle_callback_query(callback_query: dict, db: AsyncSession):
    """Handle callback queries from inline keyboards"""
    callback_id = callback_query['id']
    chat_id = callback_query['message']['chat']['id']
    user_id = callback_query['from']['id']
    data = callback_query['data']
    
    result = await db.execute(select(User).where(User.telegram_id == str(user_id)))
    user = result.scalar_one_or_none()
    
    if data == "cmd_problem":
        await handle_problem_command(chat_id, user, db)
    elif data == "cmd_balance":
        await handle_balance_command(chat_id, user, db)
    elif data == "cmd_leaderboard":
        await handle_leaderboard_command(chat_id, db)
    elif data == "cmd_help":
        await handle_help_command(chat_id)
    elif data == "cmd_start":
        username = callback_query['from'].get('username', '')
        first_name = callback_query['from'].get('first_name', '')
        await handle_start_command(chat_id, user, db, username, first_name, user_id)
    elif data == "cmd_stats":
        await handle_stats_command(chat_id, db)
    
    await telegram_service.answer_callback_query(callback_id)


async def handle_leaderboard_command(chat_id: int, db: AsyncSession):
    """Show leaderboard of top winners"""
    try:
        winner_query = select(
            User,
            func.count(PrizePool.id).label('wins'),
            func.sum(PrizePool.pool_amount * 0.8).label('total_won')
        ).join(
            PrizePool,
            User.id == PrizePool.winner_user_id
        ).group_by(
            User.id
        ).order_by(
            func.count(PrizePool.id).desc()
        ).limit(10)
        
        winners_result = await db.execute(winner_query)
        winners = winners_result.all()
        
        if not winners:
            message = """
🏆 <b>Leaderboard</b>

No winners yet! Be the first to solve a problem.

Use /problem to see the current challenge.
            """
            await telegram_service.send_message(chat_id, message)
            return
        
        leaderboard_lines = ["🏆 <b>Top Winners</b>\n"]

        for i, (user, wins, total_won) in enumerate(winners, 1):
            user_display = f"User {user.telegram_id[:5]}..."
            leaderboard_lines.append(f"{i}. {user_display}: {wins} wins, ${float(total_won):.2f} total")
        
        message = "\n".join(leaderboard_lines)
        message += "\n\nUse /problem to see the current challenge!"
        
        await telegram_service.send_message(chat_id, message)
    
    except Exception as e:
        print(f"Error in leaderboard: {e}")
        message = "❌ Error fetching leaderboard. Please try again later."
        await telegram_service.send_message(chat_id, message)

async def handle_stats_command(chat_id: int, db: AsyncSession):
    """Show game statistics"""
    try:
        problem_count = await db.execute(select(func.count(Problem.id)))
        total_problems = problem_count.scalar_one()
        
        attempt_count = await db.execute(select(func.count(Attempt.id)))
        total_attempts = attempt_count.scalar_one()
        
        winner_count = await db.execute(
            select(func.count(PrizePool.id)).where(PrizePool.winner_user_id.isnot(None))
        )
        solved_problems = winner_count.scalar_one()
        
        total_paid_query = await db.execute(
            select(func.sum(PrizePool.pool_amount * 0.8)).where(PrizePool.paid_out == True)
        )
        total_paid = total_paid_query.scalar_one() or 0
        
        current_problem = await game_service.get_current_problem(db)
        current_pool = 0
        hours_elapsed = 0
        
        if current_problem:
            current_pool = await game_service.get_current_prize_pool(current_problem.id, db)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            problem_created = current_problem.created_at
            
            if problem_created.tzinfo is None:
                problem_created = problem_created.replace(tzinfo=timezone.utc)
            
            hours_elapsed = (now - problem_created).total_seconds() / 3600
            current_cost = game_service.calculate_attempt_cost(problem_created)
        
        message = f"""
📊 <b>Game Statistics</b>

• Problems Created: {total_problems}
• Problems Solved: {solved_problems}
• Total Attempts: {total_attempts}
• Total Prizes Paid: ${float(total_paid):.2f}

🧩 <b>Current Problem</b>
• Prize Pool: ${float(current_pool):.2f}
• Running for: {hours_elapsed:.1f} hours
• Current Cost: ${current_cost:.2f}

Use /problem to see the challenge!
        """
        
        await telegram_service.send_message(chat_id, message)
    
    except Exception as e:
        print(f"Error in stats: {e}")
        message = "❌ Error fetching statistics. Please try again later."
        await telegram_service.send_message(chat_id, message)    

async def handle_start_command(chat_id: int, user: User, db: AsyncSession, username: str, first_name: str, user_id: int):
    """Handle /start command"""
    if not user:
        new_user = User(
            telegram_id=str(user_id),
            payman_id=None,
            payman_access_token=None
        )
        db.add(new_user)
        await db.commit()
        user = new_user

    if user.payman_access_token:
        validation_result = await payman_service.validate_token(user, db)
        if not validation_result.get("valid", False):
            user.payman_access_token = None
            user.token_expires_at = None
            await db.commit()
            print(f"⚠️ Cleared invalid token for user {user_id}: {validation_result.get('message')}")        
    
    if not user.payman_access_token:
        connect_url = f"{settings.PAYMAN_REDIRECT_URI.replace('/callback', '/connect')}?user_id={user_id}"
        
        welcome_message = f"""
🎯 <b>Welcome to Lydia!</b> 

Hello {first_name}! I'm your AI game master.

To play, you need to connect your Payman wallet:

🔗 <b><a href="{connect_url}">Connect Your Payman Wallet</a></b>

After connecting, you can:
• Pay small fees for each guess attempt
• Receive prize winnings instantly
• Participate in the prize pool

Click the link above and return here when done!
        """
    else:
        welcome_message = f"""
🎯 <b>Welcome back, {first_name}!</b>

Your wallet is connected and ready!

Type /problem to see the current challenge.
Type /balance to check your wallet.
        """
    
    await telegram_service.send_message(chat_id, welcome_message)
    await telegram_service.send_commands_menu(chat_id)


async def handle_balance_command(chat_id: int, user: User, db: AsyncSession = None):
    """Handle /balance command with wallet ID extraction"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

Connect your wallet first with /start
        """
        await telegram_service.send_message(chat_id, message)
        return
    else:
        try:
            balance_data = await payman_service.get_balance(user.payman_access_token)
            if balance_data.get('error') == 'TOKEN_EXPIRED' or (
                isinstance(balance_data.get('details'), str) and '401' in balance_data.get('details')):
                return await handle_token_error(chat_id, user, db)
            print(f"🔄 Checking wallet balance")
            print(f"✅ Balance check successful")
            print(f"Balance data: {balance_data}")
            
            if not user.payman_id or not user.payman_id.startswith("wlt-"):
                wallet_id = None
                if balance_data.get("success") and balance_data.get("balance"):
                    wallet_data = balance_data.get("balance")
                    if wallet_data.get("artifacts"):
                        for artifact in wallet_data.get("artifacts", []):
                            if artifact.get("name") == "response" and artifact.get("content"):
                                content = artifact.get("content")
                                patterns = [
                                    r'\|\s*(wlt-[a-f0-9-]+)\s*\|', 
                                    r'(wlt-[a-f0-9-]+)' 
                                ]
                                
                                for pattern in patterns:
                                    wallet_match = re.search(pattern, content)
                                    if wallet_match:
                                        wallet_id = wallet_match.group(1)
                                        print(f"✅ Found wallet ID: {wallet_id}")
                                        break
                
                if wallet_id and db:
                    user.payman_id = wallet_id
                    await db.commit()
                    print(f"✅ Updated user with wallet ID from balance check: {wallet_id}")
            
            if balance_data.get('error') == 'TOKEN_EXPIRED':
                print(f"🔄 Token expired for user {user.telegram_id}, clearing stored token")
                
                if db:
                    user.payman_access_token = None
                    user.payman_id = None
                    await db.commit()
                
                connect_url = f"{settings.PAYMAN_REDIRECT_URI.replace('/callback', '/connect')}?user_id={user.telegram_id}"
                
                message = f"""
🔄 <b>Token Expired</b>

Your Payman wallet connection has expired. Please reconnect:

🔗 <b><a href="{connect_url}">Reconnect Your Payman Wallet</a></b>

This happens periodically for security. After reconnecting, your balance will be available again.
                """
            
            elif balance_data.get('success'):
                wallet_response = balance_data.get('balance', {})
                
                if isinstance(wallet_response, dict) and wallet_response.get('artifacts'):
                    artifacts = wallet_response.get('artifacts', [])
                    
                    wallet_info = None
                    for artifact in artifacts:
                        if artifact.get('name') == 'response':
                            wallet_info = artifact.get('content', '')
                            break
                    
                    if wallet_info:
                        wallet_id_display = f"Wallet ID: {user.payman_id[:10]}..." if user.payman_id else ""
                        
                        message = f"""
💰 <b>Your Wallet Balance</b>

{wallet_info}

<b>Status:</b> ✅ Connected
{wallet_id_display}
                        """
                    else:
                        message = """
💰 <b>Your Wallet Balance</b>

✅ Wallet connected but no balance details available.

<b>Status:</b> Connected
                        """
                else:
                    balance_text = str(wallet_response).replace('{', '').replace('}', '').replace("'", "")
                    message = f"""
💰 <b>Your Wallet Balance</b>

{balance_text}

<b>Status:</b> ✅ Connected
                    """
            else:
                error_msg = balance_data.get('error', 'Unknown error')
                details = balance_data.get('details', '')
                
                message = f"""
❌ <b>Balance Check Failed</b>

Error: {error_msg}
{f'Details: {details}' if details else ''}

Please try again later.
                """
                
        except Exception as e:
            print(f"🚨 Balance check exception: {str(e)}")
            message = f"""
❌ <b>Error Checking Balance</b>

Exception: {str(e)}

Your wallet connection may have expired. Try /start to reconnect.
            """
    
    await telegram_service.send_message(chat_id, message)


async def handle_help_command(chat_id: int):
    """Show help message"""
    message = """
🤖 <b>Lydia Bot - Help</b>

<b>Commands:</b>
/start - Connect wallet & start playing
/problem - Show current problem 
/balance - Check your wallet balance

<b>How to Play:</b>
1️⃣ Use /start to connect wallet
2️⃣ Check current problem with /problem
3️⃣ Send your answer as a message
4️⃣ If correct, win prize immediately! 
5️⃣ If wrong, try again (cost increases over time)

<b>Prize Info:</b>
- Prize pool grows with each attempt
- First correct answer wins 80% of pool
- 20% rolls over to next problem
- Price increases over time using Golden Ratio and e

Good luck! 🍀
    """
    await telegram_service.send_message(chat_id, message)


async def handle_problem_command(chat_id: int, user: User, db: AsyncSession):
    """Show the current problem and stats"""
    problem = await game_service.get_current_problem(db)
    
    if not problem:
        message = """
⚠️ <b>No Active Problem</b>

There's no active problem at the moment. One will be created when the first player starts.
        """
        await telegram_service.send_message(chat_id, message)
        return

    current_pool = await game_service.get_current_prize_pool(problem.id, db)
    
    attempts_result = await db.execute(
        select(func.count(Attempt.id)).where(Attempt.problem_id == problem.id)
    )
    total_attempts = attempts_result.scalar_one()

    now = datetime.utcnow()
    
    if hasattr(problem.created_at, 'tzinfo') and problem.created_at.tzinfo is not None:
        timestamp = problem.created_at.timestamp()
        problem_time = datetime.utcfromtimestamp(timestamp)
    else:
        problem_time = problem.created_at
    
    hours_elapsed = (now - problem_time).total_seconds() / 3600
    current_cost = game_service.calculate_attempt_cost(problem_time)
    
    message = f"""
🧩 <b>Current Problem</b> #{problem.id}

{problem.question}

🏆 <b>Prize Pool:</b> ${current_pool:.2f}
💰 <b>Current Cost:</b> ${current_cost:.2f}
⏱️ <b>Time Elapsed:</b> {hours_elapsed:.1f} hours
🔢 <b>Attempts:</b> {total_attempts}

<b>To solve:</b> Just type your answer and send it!
    """
    
    await telegram_service.send_message(chat_id, message)

async def handle_guess_attempt(chat_id: int, user: User, text: str, db: AsyncSession):
    """Handle user's guess/attempt"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

Please connect your Payman wallet first with /start command.
        """
        await telegram_service.send_message(chat_id, message)
        return
    
    validation_result = await payman_service.validate_token(user, db)
    if not validation_result.get("valid", False):
        return await handle_token_error(chat_id, user, db, validation_result.get("error"))
    
    result = await game_service.process_attempt(user, text, db)

    if "error" in result and "401" in str(result) or "unauthorized" in str(result).lower():
        return await handle_token_error(chat_id, user, db)

    if result.get("token_expired"):
        message = f"""
🔄 <b>Wallet Connection Expired</b>

Your Payman wallet connection has expired. Please reconnect:

/start - Connect wallet
        """
        await telegram_service.send_message(chat_id, message)
        return
    
    if "error" in result:
        message = f"""
⚠️ <b>Error</b>

{result.get("error")}

Please try again or check your wallet balance with /balance
        """
        await telegram_service.send_message(chat_id, message)
        return
    
    if result.get("success") and not result.get("is_correct"):
        pool = result.get("current_pool", 0)
        cost = result.get("cost", 0)
        hours = result.get("hours_elapsed", 0)
        
        message = f"""
❌ <b>Incorrect Answer</b>

You paid <b>${cost:.2f}</b> for this attempt.

🏆 <b>Current Prize Pool:</b> ${pool:.2f}
⏱️ <b>Time Elapsed:</b> {hours:.1f} hours

Keep trying! Send another answer as text.
        """
        await telegram_service.send_message(chat_id, message)
        return
    
    if result.get("is_winner"):
        winner_payout = result.get("winner_payout", 0)
        total_pool = result.get("total_pool", 0)
        rollover = result.get("rollover_amount", 0)
        cost = result.get("cost", 0)
        new_problem = result.get("new_problem", {})
        
        message = f"""
🎉 <b>CONGRATULATIONS! YOU WON!</b> 🎉

You solved the problem correctly and won:
💰 <b>${winner_payout:.2f}</b> of the ${total_pool:.2f} prize pool!

Your final attempt cost: ${cost:.2f}
Payout Status: {"✅ Sent to your wallet!" if result.get("payout_result", {}).get("success") else "⏳ Processing..."}

${rollover:.2f} has been rolled over to the next problem:

🆕 <b>New Problem:</b>
{new_problem.get("question")}

Good luck!
        """
        await telegram_service.send_message(chat_id, message)
        return
    

async def handle_token_error(chat_id: int, user: User, db: AsyncSession, error_type: str = "TOKEN_EXPIRED"):
    """Handle token errors consistently"""
    user.payman_access_token = None
    user.token_expires_at = None
    await db.commit()
    
    connect_url = f"{settings.PAYMAN_REDIRECT_URI.replace('/callback', '/connect')}?user_id={user.telegram_id}"
    
    message = f"""
⚠️ <b>Wallet Connection Error</b>

Your Payman wallet connection has expired or is invalid.

🔄 <b><a href="{connect_url}">Reconnect Your Wallet</a></b>

This happens periodically for security reasons. After reconnecting, you'll be able to continue playing.
    """
    
    await telegram_service.send_message(chat_id, message)
    return {"token_expired": True}    