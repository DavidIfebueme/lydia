import httpx
from typing import Dict, Any, Optional
from app.config import settings

class PaymanService:
    def __init__(self):
        self.payman_service_url = "http://localhost:3001"
        self.client_id = settings.PAYMAN_CLIENT_ID
        self.redirect_uri = settings.PAYMAN_REDIRECT_URI
    
    def generate_oauth_url(self, telegram_user_id: str) -> str:
        """Generate Payman OAuth URL for user"""
        # According to Payman docs, we should use their Connect Button script
        # For now, return the redirect URI that will show the connect button
        return f"{self.redirect_uri}?user_id={telegram_user_id}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.payman_service_url}/oauth/exchange",
                json={"code": code}
            )
            if response.status_code != 200:
                return {"error": f"Token exchange failed: {response.text}"}
            return response.json()
    
    async def charge_user(self, access_token: str, amount: float, description: str, user_id: str) -> Dict[str, Any]:
        """Charge user for attempt"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.payman_service_url}/charge",
                json={
                    "accessToken": access_token,
                    "amount": amount,
                    "description": description,
                    "userId": user_id
                }
            )
            return response.json()
    
    async def payout_winner(self, access_token: str, amount: float, user_id: str, description: str) -> Dict[str, Any]:
        """Pay out winnings to user"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.payman_service_url}/payout",
                json={
                    "accessToken": access_token,
                    "amount": amount,
                    "userId": user_id,
                    "description": description
                }
            )
            return response.json()
    
    async def get_balance(self, access_token: str) -> Dict[str, Any]:
        """Get user's wallet balance"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.payman_service_url}/balance",
                json={"accessToken": access_token}
            )
            return response.json()

payman_service = PaymanService()