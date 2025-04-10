import logging
import requests
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен и чат ID для бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Загружаем токен из .env
CHAT_ID = os.getenv('CHAT_ID')  # Загружаем chat_id из .env

# Email настройки
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')  # Загружаем email отправителя
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')  # Загружаем пароль из .env
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')  # Загружаем email получателя

# Список проверяемых сайтов
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

# Функция отправки email
def send_email(subject, body):
    try:
        # Настройка MIME для email
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Отправка email через SMTP сервер
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Защищенное соединение
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            logging.info(f"Email отправлен на {RECEIVER_EMAIL}")
    except Exception as e:
        logging.error(f"Ошибка при отправке email: {str(e)}")

# Функция проверки сайтов
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

# Функция обработки команды /start
async def start(update: Update, context: ContextTypes):
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

# Функция обработки нажатия на кнопку
async def button_handler(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()
    result = check_sites()
    await query.edit_message_text("\n".join(result))

# Фоновая проверка сайтов
async def background_check(app):
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        # Проверяем на ошибки
        if any("❌" in r or "⚠️" in r for r in result):
            problems = "\n".join(result)
            # Отправляем email, если есть проблемы
            send_email("Проблемы с сайтами", "⚠️ Проблемы:\n" + problems)
            await app.bot.send_message(chat_id=CHAT_ID, text="⚠️ Проблемы:\n" + problems)
        await asyncio.sleep(300)

# Основная функция для запуска бота
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(background_check(app))
    logging.info("Бот запущен")
    await app.run_polling()

# Основной блок для запуска
if __name__ == "__main__":
    try:
        # Используем текущий цикл событий
        loop = asyncio.get_event_loop()

        # Если цикл уже запущен, добавляем задачу
        if loop.is_running():
            logging.warning("Цикл событий уже запущен.")
            loop.create_task(main())  # Запускаем задачу в уже работающем цикле
        else:
            loop.run_until_complete(main())  # Запускаем цикл событий для первой инициализации

    except Exception as e:
        logging.error(f"Ошибка: {e}")
