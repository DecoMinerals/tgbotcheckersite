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
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Токен и чат-идентификатор из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Список сайтов для проверки
SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
]

# Настройки логирования
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Проверка сайтов
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

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

# Обработчик нажатия кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result = check_sites()
    await query.edit_message_text("\n".join(result))

# Фоновая проверка сайтов
async def background_check(app):
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        if any("❌" in r or "⚠️" in r for r in result):
            await app.bot.send_message(chat_id=CHAT_ID, text="⚠️ Проблемы:\n" + "\n".join(result))
        await asyncio.sleep(300)  # Проверка каждые 5 минут

# Основная функция запуска бота
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(background_check(app))
    logging.info("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
