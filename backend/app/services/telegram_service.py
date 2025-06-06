import httpx
from typing import Dict, Any
from app.config import settings

class TelegramService:
    def __init__(self):
        self.token = settings.TELEGRAM_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    async def send_message(self, chat_id: int, text: str, reply_markup: Dict = None):
        """Send a message to a Telegram chat"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def set_webhook(self, webhook_url: str):
        """Set the webhook URL for receiving updates"""
        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    def parse_message(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming Telegram update"""
        if "message" not in update:
            return None
        
        message = update["message"]
        return {
            "chat_id": message["chat"]["id"],
            "user_id": message["from"]["id"],
            "username": message["from"].get("username"),
            "first_name": message["from"].get("first_name"),
            "text": message.get("text", ""),
            "message_id": message["message_id"]
        }

telegram_service = TelegramService()