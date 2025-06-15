import httpx
from typing import Dict, Any, Optional
from app.config import settings

class PaymanService:
    def __init__(self):
        self.payman_service_url = "http://localhost:3001" #move to env
        self.client_id = settings.PAYMAN_CLIENT_ID
        self.redirect_uri = settings.PAYMAN_REDIRECT_URI
    
    def generate_oauth_url(self, telegram_user_id: str) -> str:
        """Generate Payman OAuth URL for user"""
        return f"{self.redirect_uri.replace('/callback', '/connect')}?user_id={telegram_user_id}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                        "userId": user_id
                    }
                )
                
                response_data = response.json()
                
                if response.status_code == 401 or "unauthorized" in str(response_data).lower() or "expired" in str(response_data).lower():
                    return {"error": "TOKEN_EXPIRED", "details": "Access token has expired"}
                
                return response_data
                
        except Exception as e:
            return {"error": f"Network error during charge: {str(e)}"}
    
    async def payout_winner(self, access_token: str, amount: float, user_id: str, description: str) -> Dict[str, Any]:
        """Pay out winnings to user with token validation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/payout",
                    json={
                        "accessToken": access_token,
                        "amount": amount,
                        "userId": user_id,
                        "description": description
                    }
                )
                
                response_data = response.json()
                
                # Check for token expiration
                if response.status_code == 401 or "unauthorized" in str(response_data).lower() or "expired" in str(response_data).lower():
                    return {"error": "TOKEN_EXPIRED", "details": "Access token has expired"}
                
                return response_data
                
        except Exception as e:
            return {"error": f"Network error during payout: {str(e)}"}
    
    async def get_balance(self, access_token: str) -> Dict[str, Any]:
        """Get user's wallet balance with proper error handling and token validation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.payman_service_url}/balance",
                    json={"accessToken": access_token}
                )
                
                print(f"🔍 Balance response status: {response.status_code}") 
                print(f"🔍 Balance response text: {response.text}") 
                
                # Check for successful HTTP response
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        print(f"🔍 Parsed response data: {response_data}")
                        
                        # Check for token expiration in the response
                        if ("error" in response_data and 
                            ("unauthorized" in str(response_data["error"]).lower() or 
                             "expired" in str(response_data["error"]).lower() or
                             "token" in str(response_data["error"]).lower())):
                            return {
                                "success": False,
                                "error": "TOKEN_EXPIRED",
                                "details": "Access token has expired"
                            }
                        
                        # Check if the response indicates success
                        if response_data.get('success'):
                            return {
                                "success": True,
                                "balance": response_data.get('balance'),
                                "method": "payman_api"
                            }
                        else:
                            return {
                                "success": False,
                                "error": response_data.get('error', 'Unknown error from Payman service'),
                                "details": response_data.get('details', 'No additional details')
                            }
                            
                    except Exception as json_error:
                        print(f"🚨 JSON parsing error: {str(json_error)}")
                        return {
                            "success": False,
                            "error": f"Invalid JSON response: {str(json_error)}"
                        }
                
                # Handle HTTP errors
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": "TOKEN_EXPIRED",
                        "details": "HTTP 401 - Access token has expired"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except httpx.TimeoutException:
            print("🚨 Balance service timeout")
            return {
                "success": False,
                "error": "Request timeout - Payman servers may be slow"
            }
        except httpx.ConnectError:
            print("🚨 Balance service connection error")
            return {
                "success": False,
                "error": "Connection failed - Payman service may be down"
            }
        except Exception as e:
            print(f"🚨 Balance service exception: {str(e)}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }

payman_service = PaymanService()