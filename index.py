import logging
import requests
import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TELEGRAM_TOKEN = 'YOUR_TOKEN'
CHAT_ID = 'YOUR_CHAT_ID'

SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
]

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def check_sites():
    result = []
    for site in SITES:
        try:
            response = requests.get(site, timeout=10)
            if response.status_code == 200:
                status = "✅ работает"
            else:
                status = f"⚠️ код {response.status_code}"
            logging.info(f"{site} — {status}")
        except requests.exceptions.RequestException as e:
            status = f"❌ ошибка: {e}"
            logging.error(f"{site} — {status}")
        result.append(f"{site} — {status}")
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result = check_sites()
    await query.edit_message_text("\n".join(result))

async def background_check(app):
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        if any("❌" in r or "⚠️" in r for r in result):
            await app.bot.send_message(chat_id=CHAT_ID, text="⚠️ Проблемы:\n" + "\n".join(result))
        await asyncio.sleep(300)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(background_check(app))
    logging.info("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
