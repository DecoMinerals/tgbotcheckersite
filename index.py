import logging
import requests
import time
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import asyncio

TELEGRAM_TOKEN = '7487235916:AAFijvFJ_n1ip-EckW7jr1rFYqgZsDX7EGc'
CHAT_ID = '1911443016'

SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
]

# Настройка логирования
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
                status = f"⚠️ ошибка: код {response.status_code}"
            logging.info(f"{site} — {status}")
        except requests.exceptions.RequestException as e:
            status = f"❌ недоступен: {e}"
            logging.error(f"{site} — {status}")
        result.append(f"{site} — {status}")
    return result

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для мониторинга сайтов.", reply_markup=reply_markup)

# Обработка кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result = check_sites()
    message = "\n".join(result)
    await query.edit_message_text(text=message)

# Фоновая проверка каждые 5 минут
async def background_check(app):
    while True:
        logging.info("Запуск фоновой проверки сайтов")
        result = check_sites()
        if any("❌" in r or "⚠️" in r for r in result):
            msg = "\n".join(result)
            await app.bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Обнаружены проблемы:\n{msg}")
        await asyncio.sleep(300)

# Запуск бота
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    asyncio.create_task(background_check(app))  # Фоновая проверка

    logging.info("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
