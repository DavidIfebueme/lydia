from fastapi import FastAPI
from app.api.routes import telegram_webhook, payman_oauth

app = FastAPI(title="Lydia - AI Puzzle Game")

app.include_router(telegram_webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(payman_oauth.router, prefix="/oauth", tags=["oauth"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    """Set up webhook on startup"""
    from app.services.telegram_service import telegram_service
    from app.config import settings
    
    if settings.TELEGRAM_WEBHOOK_URL != "https://yourdomain.com/webhook/telegram":
        result = await telegram_service.set_webhook(settings.TELEGRAM_WEBHOOK_URL)
        print(f"Webhook setup result: {result}")