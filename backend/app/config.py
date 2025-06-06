import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_URL: str = os.getenv("DATABASE_URL")
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
    PAYMAN_CLIENT_ID: str = os.getenv("PAYMAN_CLIENT_ID")
    PAYMAN_CLIENT_SECRET: str = os.getenv("PAYMAN_CLIENT_SECRET")
    PAYMAN_REDIRECT_URI: str = os.getenv("PAYMAN_REDIRECT_URI")

settings = Settings()