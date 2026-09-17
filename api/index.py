import os
import sys

# Add parent directory to path to allow importing main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from aiogram.types import Update
from main import bot, dp

app = FastAPI()

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update(**update_data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        print("Webhook Error:", e)
        return {"status": "error"}

@app.get("/api/set_webhook")
async def set_webhook(url: str):
    await bot.set_webhook(url)
    return {"status": f"Webhook set to {url}"}

@app.get("/api/webhook")
async def check_webhook():
    return {"status": "Bot webhook is active!"}

@app.get("/")
async def root():
    return {"status": "Vercel deployment working!"}
