from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.db import get_db
from app.models.user import User
from app.services.payman_service import payman_service
from app.services.telegram_service import telegram_service
from app.config import settings

import re

router = APIRouter()

@router.get("/connect")
async def oauth_connect_page(user_id: str):
    """Show Payman Connect Button page with proper message handling"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connect Your Payman Wallet</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                padding: 20px; 
                text-align: center; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{ 
                max-width: 400px; 
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }}
            h1 {{ color: #fff; margin-bottom: 20px; }}
            p {{ color: #f0f0f0; margin: 15px 0; }}
            .debug {{ font-size: 12px; margin-top: 20px; opacity: 0.7; }}
            .status {{ 
                margin-top: 20px; 
                padding: 10px; 
                border-radius: 5px; 
                background: rgba(255,255,255,0.1); 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Connect Your Wallet</h1>
            <p>Click the button below to connect your Payman wallet to Lydia:</p>
            <div id="payman-connect"></div>
            <p><small>After connecting, you'll be redirected automatically!</small></p>
            
            <div id="status" class="status" style="display: none;">
                <p id="status-text">Processing...</p>
            </div>
            
            <div class="debug">
                <p>Debug Info:</p>
                <p>User ID: {user_id}</p>
                <p>Redirect: {settings.PAYMAN_REDIRECT_URI}</p>
            </div>
        </div>
        
        <!-- Payman Connect Button Script -->
        <script
            src="https://app.paymanai.com/js/pm.js"
            data-client-id="{settings.PAYMAN_CLIENT_ID}"
            data-scopes="read_balance,read_list_wallets,read_list_payees,read_list_transactions,write_create_payee,write_send_payment,write_create_wallet"
            data-redirect-uri="{settings.PAYMAN_REDIRECT_URI}"
            data-target="#payman-connect"
            data-dark-mode="false"
            data-styles='{{"borderRadius": "8px", "fontSize": "16px", "padding": "12px 24px"}}'></script>
            
        <script>
            console.log('OAuth page loaded for user:', '{user_id}');
            localStorage.setItem('telegram_user_id', '{user_id}');
            
            // Status update function
            function updateStatus(message, isError = false) {{
                const statusDiv = document.getElementById('status');
                const statusText = document.getElementById('status-text');
                statusDiv.style.display = 'block';
                statusDiv.style.background = isError ? 'rgba(255,0,0,0.2)' : 'rgba(0,255,0,0.2)';
                statusText.textContent = message;
            }}
            
            // Handle OAuth redirect messages (OFFICIAL PAYMAN WAY)
            window.addEventListener("message", function (event) {{
                console.log('Received message event:', event.data);
                
                if (event.data.type === "payman-oauth-redirect") {{
                    console.log('OAuth redirect detected!');
                    updateStatus('OAuth completed! Processing...');
                    
                    const url = new URL(event.data.redirectUri);
                    const code = url.searchParams.get("code");
                    const error = url.searchParams.get("error");
                    
                    if (error) {{
                        console.error('OAuth error:', error);
                        updateStatus('OAuth failed: ' + error, true);
                        return;
                    }}
                    
                    if (code) {{
                        console.log('Authorization code received:', code.substring(0, 20) + '...');
                        exchangeCodeForToken(code);
                    }} else {{
                        console.error('No authorization code received');
                        updateStatus('No authorization code received', true);
                    }}
                }}
            }});
            
            // Exchange code for token (FOLLOWING OFFICIAL DOCS)
            async function exchangeCodeForToken(code) {{
                try {{
                    updateStatus('Exchanging code for token...');
                    console.log('Exchanging code for token...');
                    
                    const response = await fetch('/oauth/exchange', {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ code }})
                    }});
                    
                    const result = await response.json();
                    console.log('Token exchange result:', result);
                    
                    if (result.success) {{
                        updateStatus('Token received! Updating user...');
                        console.log('Got payee ID:', result.payeeId); // Debug output
                        
                        // Update user in database
                        const telegramUserId = localStorage.getItem('telegram_user_id');
                        if (telegramUserId) {{
                            const notifyResponse = await fetch('/oauth/notify-success', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{
                                    code: code,
                                    telegram_user_id: telegramUserId,
                                    access_token: result.accessToken,
                                    payman_user_id: result.userId,
                                    payee_id: result.payeeId,
                                    expires_in: result.expiresIn || 600
                                }})
                            }});
                            
                            const notifyResult = await notifyResponse.json();
                            console.log('Notification result:', notifyResult);
                            
                            if (notifyResult.success) {{
                                updateStatus(`✅ Wallet connected successfully!${{result.payeeId ? ' Payee ID received.' : ''}}`);
                                setTimeout(() => {{
                                    window.close();
                                }}, 2000);
                            }} else {{
                                updateStatus('Failed to update user: ' + notifyResult.error, true);
                            }}
                        }} else {{
                            updateStatus('No telegram user ID found', true);
                        }}
                    }} else {{
                        updateStatus('Token exchange failed: ' + result.error, true);
                    }}
                }} catch (error) {{
                    console.error('Exchange failed:', error);
                    updateStatus('Exchange failed: ' + error.message, true);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/exchange")
async def oauth_token_exchange(request: Request):
    """Exchange OAuth code for access token (following official docs)"""
    try:
        data = await request.json()
        code = data.get("code")
        
        if not code:
            return {"success": False, "error": "No authorization code provided"}

        token_data = await payman_service.exchange_code_for_token(code)
        
        if "error" in token_data:
            return {"success": False, "error": token_data["error"]}
        
        return {
            "success": True,
            "accessToken": token_data.get("accessToken"),
            "expiresIn": token_data.get("expiresIn"),
            "userId": token_data.get("userId"),
            "payeeId": token_data.get("payeeId"),
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/callback")
async def oauth_callback(request: Request):
    """Simple callback endpoint (fallback)"""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        return HTMLResponse(f"""
            <h1>❌ OAuth Error</h1>
            <p>Error: {error}</p>
            <p>Please try again.</p>
        """)
    
    if code:
        return HTMLResponse(f"""
            <h1>✅ Authorization Code Received</h1>
            <p>Code: {code[:20]}...</p>
            <p>This should be handled by the message listener.</p>
            <script>
                // Send message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'payman-oauth-redirect',
                        redirectUri: window.location.href
                    }}, '*');
                    window.close();
                }}
            </script>
        """)
    
    return HTMLResponse("<h1>❌ No authorization code received</h1>")

@router.post("/notify-success")
async def notify_success(request: Request, db: AsyncSession = Depends(get_db)):
    """Update user with OAuth success and fetch wallet ID"""
    try:
        data = await request.json()
        telegram_user_id = data.get("telegram_user_id")
        access_token = data.get("access_token")
        payee_id = data.get("payee_id")
        
        print(f"🔄 Received OAuth success for Telegram user {telegram_user_id}")
        
        result = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User {telegram_user_id} not found")
            return {"success": False, "error": "User not found"}
        
        user.payman_access_token = access_token
        user.payman_payee_id = payee_id

        expires_in = data.get("expires_in", 600)
        user.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        await db.commit()
        
        print("🔄 Getting wallet ID via balance check...")
        balance_data = await payman_service.get_balance(access_token)
        print(f"🔍 Balance data received, extracting wallet ID...")
        
        wallet_id = None
        if balance_data.get("success") and balance_data.get("balance"):
            wallet_data = balance_data.get("balance")
            
            if isinstance(wallet_data, dict):
                print(f"🔍 Keys in wallet_data: {list(wallet_data.keys())}")
                
                if wallet_data.get("artifacts"):
                    artifacts = wallet_data.get("artifacts")
                    print(f"🔍 Found {len(artifacts)} artifacts")
                    
                    for i, artifact in enumerate(artifacts):
                        if artifact.get("name") == "response" and artifact.get("content"):
                            content = artifact.get("content")
                            print(f"🔍 Found response content in artifact #{i}")
                            
                            patterns = [
                                r'Wallet ID.*?(\bwlt-[a-f0-9-]+)',
                                r'\|\s*(wlt-[a-f0-9-]+)\s*\|',
                                r'(wlt-[a-f0-9-]+)'
                            ]
                            
                            for pattern in patterns:
                                wallet_match = re.search(pattern, content)
                                if wallet_match:
                                    wallet_id = wallet_match.group(1)
                                    print(f"✅ Found wallet ID using pattern {pattern}: {wallet_id}")
                                    break
                            
                            if not wallet_id:
                                print("❌ No wallet ID found in content. Raw content:")
                                print(content[:500])
        
        if wallet_id:
            user.payman_id = wallet_id 
            await db.commit()
            
            await telegram_service.send_message(
                int(telegram_user_id),
                f"""
🎉 <b>Wallet Connected Successfully!</b>

Your Payman wallet is now linked to Lydia!
Wallet ID: {wallet_id[:10]}...

You can now:
✅ Make guess attempts
✅ Participate in prize pools
✅ Receive winnings instantly

Type /problem to see the current challenge!
                """
            )
            await telegram_service.send_commands_menu(int(telegram_user_id))
            
            return {"success": True, "wallet_id": wallet_id}
        else:
            print("⚠️ WARNING: Could not extract wallet ID from balance response")
            
            if isinstance(balance_data.get("balance"), dict) and balance_data.get("balance").get("artifacts"):
                try:
                    artifacts = balance_data.get("balance").get("artifacts")
                    for artifact in artifacts:
                        if artifact.get("name") == "response" and artifact.get("content"):
                            content = artifact.get("content")
                            rows = content.split("\n")
                            print("Table parsing attempt:")
                            for row in rows:
                                if "wlt-" in row:
                                    print(f"Found wallet ID row: {row}")
                except Exception as parse_error:
                    print(f"Error parsing table: {parse_error}")
            
            await telegram_service.send_message(
                int(telegram_user_id),
                """
🔄 <b>Wallet Partially Connected</b>

Your Payman auth was successful, but we couldn't retrieve your wallet ID.

Try using the /balance command. If you see your wallet balance, the connection will complete automatically.
                """
            )
            
            return {"success": True, "wallet_id": None, "warning": "No wallet ID found"}
            
    except Exception as e:
        print(f"❌ Error in notify-success: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}