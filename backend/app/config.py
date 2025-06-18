import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_URL: str = os.getenv("DATABASE_URL")
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_WEBHOOK_URL: str = os.getenv("TELEGRAM_WEBHOOK_URL", "https://yourdomain.com/webhook/telegram")
    PAYMAN_CLIENT_ID: str = os.getenv("PAYMAN_CLIENT_ID")
    PAYMAN_CLIENT_SECRET: str = os.getenv("PAYMAN_CLIENT_SECRET")
    PAYMAN_REDIRECT_URI: str = os.getenv("PAYMAN_REDIRECT_URI")
    PAYMAN_APP_WALLET_ID: str = os.getenv("PAYMAN_APP_WALLET_ID")
    PAYMAN_SERVICE_URL: str = os.getenv("PAYMAN_SERVICE_URL")
    APP_PAYMAN_ACCESS_TOKEN: str = os.getenv("APP_PAYMAN_ACCESS_TOKEN")


settings = Settings()