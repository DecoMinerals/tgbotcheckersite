import nest_asyncio
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

# Разрешаем вложенные asyncio события
nest_asyncio.apply()

# Токены и конфигурация
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
    # Кнопка для проверки сайтов
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработка нажатия на кнопку
    query = update.callback_query
    await query.answer()
    result = check_sites()
    await query.edit_message_text("\n".join(result))

async def background_check(app):
    # Фоновая проверка сайтов каждую минуту
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        if any("❌" in r or "⚠️" in r for r in result):
            await app.bot.send_message(chat_id=CHAT_ID, text="⚠️ Проблемы:\n" + "\n".join(result))
        await asyncio.sleep(300)  # Задержка в 5 минут

async def main():
    # Инициализация приложения и обработчиков
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Запуск фона проверки
    asyncio.create_task(background_check(app))

    logging.info("Бот запущен и работает")
    try:
        await app.run_polling()  # Запуск polling
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        await app.bot.send_message(chat_id=CHAT_ID, text="Произошла ошибка при запуске бота.")

if __name__ == "__main__":
    asyncio.run(main())
