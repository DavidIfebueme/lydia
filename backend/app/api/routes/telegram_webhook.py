from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.telegram_service import telegram_service
from app.models.user import User
from sqlalchemy import select
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
            await handle_problem_command(chat_id, user)
        else:
            await handle_guess_attempt(chat_id, user, text, db)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error"}

async def handle_start_command(chat_id: int, user: User, db: AsyncSession, username: str, first_name: str, user_id: int):
    """Handle /start command"""
    if not user:
        # New user - need to register via Payman OAuth
        welcome_message = f"""
🎯 <b>Welcome to Lydia!</b> 

Hello {first_name}! I'm your AI riddle master. 

To play, you need to connect your Payman wallet first. This allows you to:
• Pay small fees for each guess attempt
• Receive prize winnings instantly
• Participate in the prize pool

<b>How to get started:</b>
1. Click the link below to connect your Payman wallet
2. Complete the OAuth flow
3. Return here to start solving problems!

Connect your wallet: [Payman OAuth Link - Coming Soon]

Type /help for more information.
        """
        
        # Create user record (without Payman details yet)
        new_user = User(
            telegram_id=str(user_id),
            payman_id=None,
            payman_access_token=None
        )
        db.add(new_user)
        await db.commit()
        
    else:
        if user.payman_access_token:
            welcome_message = f"""
🎯 <b>Welcome back, {first_name}!</b>

You're all set up and ready to play!

Type /problem to see the current challenge.
Type /help for commands.
            """
        else:
            welcome_message = f"""
🎯 <b>Welcome back, {first_name}!</b>

You need to complete your Payman wallet connection:
[Payman OAuth Link - Coming Soon]

Once connected, you can start playing!
            """
    
    await telegram_service.send_message(chat_id, welcome_message)

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

async def handle_problem_command(chat_id: int, user: User):
    """Handle /problem command"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

You need to connect your Payman wallet first!
Type /start to get the connection link.
        """
    else:
        # TODO: Get current active problem from database
        message = """
🧩 <b>Current Challenge</b>

Problem: What gets wetter the more it dries?

💰 Current Prize Pool: $127.50
💸 Cost per Guess: $2.50

Send me your answer to make a guess!
        """
    
    await telegram_service.send_message(chat_id, message)

async def handle_guess_attempt(chat_id: int, user: User, guess: str, db: AsyncSession):
    """Handle a guess attempt"""
    if not user or not user.payman_access_token:
        message = """
❌ <b>Wallet Not Connected</b>

You need to connect your Payman wallet to make guesses!
Type /start to get started.
        """
    else:
        # TODO: Process the guess attempt
        message = f"""
🎯 <b>Guess Received!</b>

Your guess: "{guess}"

Processing payment and checking answer...
[Payment & Game Logic - Coming Soon]
        """
    
    await telegram_service.send_message(chat_id, message)