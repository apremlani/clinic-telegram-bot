"""
Webhook server for the clinic Telegram bot.
Telegram calls POST /webhook the instant a message arrives -> we run it
through engine.py -> reply immediately via Telegram's HTTP API.
This is what makes it synchronous/instant, unlike manual polling.

Reads the bot token from the TELEGRAM_BOT_TOKEN environment variable -
set this in your hosting platform's dashboard (e.g. Render), never in code,
and never share it in chat.
"""
import os
import requests
from fastapi import FastAPI, Request

import engine

app = FastAPI()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


@app.get("/")
def health():
    return {"status": "ok", "service": "clinic-telegram-bot", "token_configured": bool(BOT_TOKEN)}


@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    name = message["chat"].get("first_name", "there")
    text = message.get("text", "")

    try:
        reply = engine.handle_message(chat_id, name, text)
    except Exception as e:
        reply = f"Sorry, something went wrong on my end ({type(e).__name__}). Please try again or type /help."

    if BOT_TOKEN:
        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": reply}, timeout=10)

    return {"ok": True}
