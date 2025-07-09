from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from frankelly_telegram.bot import send_telegram_message
from frankelly_telegram.shared_state import BOT_STATE

async def _reply(chat_id: int, text: str):
    send_telegram_message(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    BOT_STATE["running"] = True
    await _reply(update.effective_chat.id, "✅ Bot started")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    BOT_STATE["running"] = False
    await _reply(update.effective_chat.id, "⏸️ Bot stopped")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = "🟢 Running" if BOT_STATE["running"] else "⏸️ Paused"
    await _reply(update.effective_chat.id, f"🤖 Status: {state}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "/start — Start trading\n"
        "/stop — Pause trading\n"
        "/status — Show status\n"
        "/help — This help"
    )
    await _reply(update.effective_chat.id, txt)

def get_command_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("stop", stop),
        CommandHandler("status", status),
        CommandHandler("help", help_cmd),
    ]

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Telegram error: {context.error}")
    if update and update.effective_chat:
        await _reply(update.effective_chat.id, f"⚠️ Error: {context.error}")
