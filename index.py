import nest_asyncio
nest_asyncio.apply()

import logging
import requests
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Конфигурация
TELEGRAM_TOKEN = '7487235916:AAFijvFJ_n1ip-EckW7jr1rFYqgZsDX7EGc'
CHAT_ID = '1911443016'

# Настройки почты (добавьте свои значения)
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
SENDER_EMAIL = 'your_email@example.com'
SENDER_PASSWORD = 'your_password'
RECEIVER_EMAIL = 'receiver@example.com'

SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
    "https://rfrp36.ru/",
]

# Настройка логирования
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def send_email(subject, body):
    """Функция отправки email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            logging.info(f"Email отправлен на {RECEIVER_EMAIL}")
    except Exception as e:
        logging.error(f"Ошибка при отправке email: {str(e)}")

def check_sites():
    """Проверка доступности сайтов"""
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
    """Обработчик команды /start"""
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    result = check_sites()
    await query.edit_message_text("\n".join(result))

async def background_check(app):
    """Фоновая проверка сайтов"""
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        
        # Если есть проблемы
        if any("❌" in r or "⚠️" in r for r in result):
            problems = "⚠️ Проблемы:\n" + "\n".join(result)
            
            # Отправляем в Telegram
            await app.bot.send_message(chat_id=CHAT_ID, text=problems)
            
            # Отправляем на почту
            send_email("Проблемы с сайтами", problems)
        
        await asyncio.sleep(30)

async def main():
    """Основная функция запуска"""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Запуск фоновой задачи
    asyncio.create_task(background_check(app))
    
    logging.info("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")