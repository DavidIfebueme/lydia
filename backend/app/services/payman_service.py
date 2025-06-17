import httpx
import re
from typing import Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.models.user import User

class PaymanService:
    def __init__(self):
        self.payman_service_url = "https://lydia-vox3.onrender.com" #move to env
        self.client_id = settings.PAYMAN_CLIENT_ID
        self.redirect_uri = settings.PAYMAN_REDIRECT_URI
    
    def generate_oauth_url(self, telegram_user_id: str) -> str:
        """Generate Payman OAuth URL for user"""
        return f"{self.redirect_uri.replace('/callback', '/connect')}?user_id={telegram_user_id}"

    async def validate_token(self, user: User) -> Dict[str, Any]:
        """Validate if the user's token is still valid"""
        if user.token_expires_at:
            now = datetime.utcnow()
            if hasattr(user.token_expires_at, 'tzinfo') and user.token_expires_at.tzinfo:
                import pytz
                now = pytz.UTC.localize(now)
            
            if now >= user.token_expires_at:
                return {
                    "valid": False,
                    "error": "TOKEN_EXPIRED", 
                    "message": "Stored token has expired"
                }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/balance",
                    json={"accessToken": user.payman_access_token}
                )
                
                if response.status_code == 401:
                    return {
                        "valid": False,
                        "error": "TOKEN_EXPIRED",
                        "message": "Token check failed with 401 Unauthorized"
                    }
                    
                if response.status_code == 200:
                    return {"valid": True}

                return {
                    "valid": False,
                    "error": f"API_ERROR_{response.status_code}",
                    "message": f"API responded with status {response.status_code}: {response.text[:100]}"
                }
                    
        except Exception as e:
            return {
                "valid": False, 
                "error": "CONNECTION_ERROR",
                "message": f"Network error checking token: {str(e)}"
            }    
        
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        try:
            async with httpx.AsyncClient(timeout=100.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/oauth/exchange",
                    json={"code": code}
                )
                
                if response.status_code != 200:
                    return {"error": f"Token exchange failed: {response.text}"}
                    
                return response.json()
                
        except Exception as e:
            return {"error": f"Network error during token exchange: {str(e)}"}
    
    async def charge_user(self, access_token: str, amount: float, description: str, user_id: str) -> Dict[str, Any]:
        """Charge user for attempt with token validation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/charge",
                    json={
                        "accessToken": access_token,
                        "amount": amount,
                        "description": description,
                        "userId": user_id,
                    }
                )
                
                if response.status_code == 401:
                    return {"error": "TOKEN_EXPIRED", "details": "Access token has expired (HTTP 401)"}
                    
                try:
                    response_data = response.json()
                except Exception:
                    return {
                        "error": f"Invalid response (HTTP {response.status_code})", 
                        "details": response.text[:100]
                    }
                
                if not response.status_code == 200 or "error" in response_data:
                    return {
                        "error": response_data.get("error", f"HTTP {response.status_code} error"),
                        "details": response_data.get("details", response.text[:100])
                    }
                
                return response_data
                    
        except Exception as e:
            return {"error": f"Network error during charge: {str(e)}"}
    
    async def payout_winner(self, access_token: str, amount: float, payee_id: str, description: str) -> Dict[str, Any]:
        """Pay out winnings to user with token validation"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/payout",
                    json={
                        "accessToken": access_token,
                        "amount": amount,
                        "payeeId": payee_id,
                        "description": description
                    }
                )
                
                response_data = response.json()
                
                if response.status_code == 401 or "unauthorized" in str(response_data).lower() or "expired" in str(response_data).lower():
                    return {"error": "TOKEN_EXPIRED", "details": "Access token has expired"}
                
                return response_data
                
        except Exception as e:
            return {"error": f"Network error during payout: {str(e)}"}
    
    async def get_balance(self, access_token: str) -> Dict[str, Any]:
        """Get user's wallet balance with wallet ID extraction"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/balance",
                    json={"accessToken": access_token}
                )
                
                print(f"🔍 Balance response status: {response.status_code}") 
                
                if response.status_code == 401:
                    return {
                        "success": False,
                        "error": "TOKEN_EXPIRED",
                        "details": "HTTP 401 - Access token has expired"
                    }
                    
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP error {response.status_code}",
                        "details": response.text
                    }
                    
                try:
                    response_data = response.json()
                    
                    wallet_id = None
                    
                    if response_data.get('success') and response_data.get('balance'):
                        balance_data = response_data.get('balance')
                        
                        if isinstance(balance_data, dict) and balance_data.get('artifacts'):
                            artifacts = balance_data.get('artifacts', [])
                            
                            for artifact in artifacts:
                                if artifact.get('name') == 'response' and artifact.get('content'):
                                    content = artifact.get('content')

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
                    
                    return {
                        "success": True,
                        "balance": response_data.get('balance'),
                        "wallet_id": wallet_id
                    }
                        
                except Exception as json_error:
                    print(f"🚨 JSON parsing error: {str(json_error)}")
                    return {
                        "success": False,
                        "error": f"Invalid response: {str(json_error)}"
                    }
                    
        except Exception as e:
            print(f"🚨 Balance service exception: {str(e)}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }

payman_service = PaymanService()