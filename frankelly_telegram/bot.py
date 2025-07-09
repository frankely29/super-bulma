import os
import requests

def send_telegram_message(message: str, force_send=False):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        res = requests.post(url, data=payload)
        res.raise_for_status()
        print("✅ Telegram message sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def start_telegram_bot():
    send_telegram_message("🤖 Frankelly Bot is now running.")