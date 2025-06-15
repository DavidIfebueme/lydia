from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.telegram_service import telegram_service
from app.services.payman_service import payman_service
from app.services.game_service import game_service
from app.models.user import User
from app.config import settings
from sqlalchemy import select
from datetime import datetime, timedelta
import json

router = APIRouter()

@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Telegram updates"""
    try:
        update = await request.json()
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
        else:
            await handle_guess_attempt(chat_id, user, text, db)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error"}

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
    
    if not user.payman_access_token:
        connect_url = f"{settings.PAYMAN_REDIRECT_URI.replace('/callback', '/connect')}?user_id={user_id}"
        
        welcome_message = f"""
🎯 <b>Welcome to Lydia!</b> 

Hello {first_name}! I'm your AI puzzle master.

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


async def handle_balance_command(chat_id: int, user: User, db: AsyncSession = None):
    """Handle /balance command with token expiration handling"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

Connect your wallet first with /start
        """
    else:
        try:
            balance_data = await payman_service.get_balance(user.payman_access_token)
            #print(f"🔍 Balance data received: {balance_data}")
            
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
                
                # Extract wallet information from the AI response
                if isinstance(wallet_response, dict) and wallet_response.get('status') == 'COMPLETED' and 'artifacts' in wallet_response:
                    artifacts = wallet_response.get('artifacts', [])
                    
                    # Find the response artifact
                    wallet_info = None
                    for artifact in artifacts:
                        if artifact.get('name') == 'response':
                            wallet_info = artifact.get('content', '')
                            break
                    
                    if wallet_info:
                        clean_wallet_info = wallet_info.replace('|', '').replace('-', '').strip()
                        
                        message = f"""
💰 <b>Your Wallet Balance</b>

{clean_wallet_info}

<b>Status:</b> ✅ Connected
<b>Last Updated:</b> {wallet_response.get('timestamp', 'Unknown')[:19]}
                        """
                    else:
                        message = """
💰 <b>Your Wallet Balance</b>

✅ Wallet connected but no balance details available.

<b>Status:</b> Connected
                        """
                elif isinstance(wallet_response, dict):
                    balance_text = str(wallet_response).replace('{', '').replace('}', '').replace("'", "")
                    message = f"""
💰 <b>Your Wallet Balance</b>

{balance_text}

<b>Status:</b> ✅ Connected
                    """
                else:
                    message = f"""
💰 <b>Your Wallet Balance</b>

{wallet_response}

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
    """Handle /help command"""
    help_message = """
🤖 <b>Lydia Commands</b>

/start - Get started or reconnect wallet
/problem - View current challenge
/help - Show this help message

<b>How to Play:</b>
1. Connect your Payman wallet
2. View the current problem/riddle
3. Submit your guess (costs a small fee)
4. First correct answer wins the prize pool!

<b>Game Rules:</b>
• Each guess costs a small amount
• Prize pool grows with each incorrect guess
• Winner gets 80% of the pool
• 20% rolls over to the next round
• Guess cost increases every 6 hours
    """
    
    await telegram_service.send_message(chat_id, help_message)

async def handle_problem_command(chat_id: int, user: User, db: AsyncSession):
    """Handle /problem command with escalation info"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

You need to connect your Payman wallet first!
Type /start to get the connection link.
        """
    else:
        problem = await game_service.get_current_problem(db)
        if not problem:
            message = """
❌ <b>No Active Problem</b>

There's currently no active problem. A new one will be available soon!
            """
        else:
            current_pool = await game_service.get_current_prize_pool(problem.id, db)
            current_cost = game_service.calculate_attempt_cost(problem.created_at)
            hours_elapsed = (datetime.utcnow() - problem.created_at).total_seconds() / 3600
            
            next_escalation_hours = ((int(hours_elapsed / 6) + 1) * 6) - hours_elapsed
            next_cost = game_service.calculate_attempt_cost(
                problem.created_at - timedelta(hours=next_escalation_hours)
            )
            
            escalation_info = ""
            if hours_elapsed > 0:
                escalation_info = f"""
⏰ <b>Time Dynamics:</b>
• Problem active for: {hours_elapsed:.1f} hours
• Next cost increase in: {next_escalation_hours:.1f} hours
• Next attempt cost: ${next_cost:.2f}
                """
            
            message = f"""
🧩 <b>Current Challenge</b>

<b>Problem:</b> {problem.question}

💰 <b>Current Prize Pool:</b> ${current_pool:.2f}
💸 <b>Attempt Cost:</b> ${current_cost:.2f}
{escalation_info}

<b>📊 Game Economics:</b>
• Winner receives: 80% (${current_pool * 0.8:.2f})
• Next game starts with: 20% (${current_pool * 0.2:.2f})

Send me your answer to make a guess!
            """
    
    await telegram_service.send_message(chat_id, message)


async def handle_guess_attempt(chat_id: int, user: User, guess: str, db: AsyncSession):
    """Handle a guess attempt with mathematical cost escalation"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

You need to connect your Payman wallet to make guesses!
Type /start to get started.
        """
        await telegram_service.send_message(chat_id, message)
        return
    
    result = await game_service.process_attempt(user, guess, db)
    
    if "error" in result:
        message = f"""
❌ <b>Attempt Failed</b>

{result['error']}

Try again or check your wallet balance!
        """
    elif result.get("is_winner"):
        message = f"""
🎉🏆 <b>WINNER! CONGRATULATIONS!</b> 🏆🎉

Your guess: "<b>{guess}</b>" is CORRECT!

💰 Attempt Cost: ${result['cost']:.2f}
🏆 Total Prize Pool: ${result['total_pool']:.2f}
💸 Your Payout: ${result['winner_payout']:.2f}
🔄 Next Game Pool: ${result['rollover_amount']:.2f}

<b>🎯 Payment processing...</b>
You'll receive your winnings shortly!

A new challenge is now active! Type /problem to see it.
        """
    elif result["is_correct"]:
        message = f"""
🎉 <b>CORRECT ANSWER!</b> 🎉

Your guess: "<b>{guess}</b>" is right!
But processing winner status...
        """
    else:
        hours_elapsed = result.get("hours_elapsed", 0)
        escalation_info = ""
        if hours_elapsed > 6:
            escalation_info = f"\n⏰ Cost escalated after {hours_elapsed:.1f} hours"
        
        message = f"""
❌ <b>Incorrect</b>

Your guess: "<b>{guess}</b>"
💰 Charged: ${result['cost']:.2f}{escalation_info}
💰 Current Prize Pool: ${result['current_pool']:.2f}

The challenge continues! Try again or wait for cost to escalate.
        """
    
    await telegram_service.send_message(chat_id, message)