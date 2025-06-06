from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models.user import User
from app.services.payman_service import payman_service
from app.services.telegram_service import telegram_service
from app.config import settings

router = APIRouter()

@router.get("/connect")
async def oauth_connect_page(user_id: str):
    """Show Payman Connect Button page"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connect Your Payman Wallet</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
            .container {{ max-width: 400px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            p {{ color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Connect Your Wallet</h1>
            <p>Click the button below to connect your Payman wallet to Lydia:</p>
            <div id="payman-connect"></div>
            <p><small>After connecting, return to Telegram to start playing!</small></p>
        </div>
        
        <script
            src="https://app.paymanai.com/js/pm.js"
            data-client-id="{settings.PAYMAN_CLIENT_ID}"
            data-scopes="read_balance,read_list_wallets,read_list_payees,read_list_transactions,write_create_payee,write_send_payment,write_create_wallet"
            data-redirect-uri="{settings.PAYMAN_REDIRECT_URI}"
            data-target="#payman-connect"
            data-dark-mode="false"
            data-styles='{{"borderRadius": "8px", "fontSize": "16px"}}'></script>
            
        <script>
            // Store user_id for callback
            localStorage.setItem('telegram_user_id', '{user_id}');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/callback")
async def oauth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Payman OAuth callback"""
    try:
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        
        if error:
            return HTMLResponse(f"""
                <h1>❌ Connection Failed</h1>
                <p>Error: {error}</p>
                <p>Please return to Telegram and try again.</p>
            """)
        
        if not code:
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        token_data = await payman_service.exchange_code_for_token(code)
        
        if "error" in token_data:
            return HTMLResponse(f"""
                <h1>❌ Token Exchange Failed</h1>
                <p>Error: {token_data['error']}</p>
                <p>Please return to Telegram and try again.</p>
            """)
        
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Wallet Connected!</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
                    .success {{ color: #28a745; }}
                </style>
            </head>
            <body>
                <h1 class="success">🎉 Wallet Connected!</h1>
                <p>Your Payman wallet has been successfully connected to Lydia.</p>
                <p><strong>You can now close this window and return to Telegram to start playing!</strong></p>
                
                <script>
                    // Try to get telegram user ID and notify the backend
                    const telegramUserId = localStorage.getItem('telegram_user_id');
                    if (telegramUserId) {{
                        fetch('/oauth/notify-success', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                code: '{code}',
                                telegram_user_id: telegramUserId,
                                access_token: '{token_data.get("accessToken", "")}',
                                user_id: '{token_data.get("userId", "")}'
                            }})
                        }});
                    }}
                </script>
            </body>
            </html>
        """)
        
    except Exception as e:
        return HTMLResponse(f"""
            <h1>❌ Connection Failed</h1>
            <p>Error: {str(e)}</p>
            <p>Please return to Telegram and try again.</p>
        """)

@router.post("/notify-success")
async def notify_success(request: Request, db: AsyncSession = Depends(get_db)):
    """Update user with OAuth success"""
    try:
        data = await request.json()
        telegram_user_id = data.get("telegram_user_id")
        access_token = data.get("access_token")
        payman_user_id = data.get("user_id")
        
        result = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
        user = result.scalar_one_or_none()
        
        if user:
            user.payman_id = payman_user_id
            user.payman_access_token = access_token
            await db.commit()
            
            await telegram_service.send_message(
                int(telegram_user_id),
                """
🎉 <b>Wallet Connected Successfully!</b>

Your Payman wallet is now linked to Lydia!

You can now:
✅ Make guess attempts
✅ Participate in prize pools
✅ Receive winnings instantly

Type /problem to see the current challenge!
                """
            )
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}