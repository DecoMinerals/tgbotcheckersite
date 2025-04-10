#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
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
import asyncio

# ===================== НАСТРОЙКА =====================
# Загружаем переменные окружения
load_dotenv()

# Конфигурация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Конфигурация почты
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))  # По умолчанию 587 порт
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')

# Список сайтов для проверки
SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# ===================== ФУНКЦИИ =====================
def send_email(subject, body):
    """Отправка email с проблемами"""
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
        logging.error(f"Ошибка отправки email: {str(e)}")

def check_sites():
    """Проверка доступности сайтов"""
    results = []
    for site in SITES:
        try:
            response = requests.get(site, timeout=10)
            if response.status_code == 200:
                status = "✅ работает"
            else:
                status = f"⚠️ код {response.status_code}"
            logging.info(f"{site} — {status}")
        except Exception as e:
            status = f"❌ ошибка: {str(e)}"
            logging.error(f"{site} — {status}")
        results.append(f"{site} — {status}")
    return results

# ===================== ОБРАБОТЧИКИ ТЕЛЕГРАМ =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для проверки сайтов.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    results = check_sites()
    await query.edit_message_text("\n".join(results))

# ===================== ФОНОВАЯ ПРОВЕРКА =====================
async def background_check(app):
    """Фоновая проверка сайтов каждые 5 минут"""
    while True:
        logging.info("Запуск фоновой проверки сайтов...")
        results = check_sites()
        
        if any("❌" in r or "⚠️" in r for r in results):
            problems = "\n".join(r for r in results if "❌" in r or "⚠️" in r)
            send_email("Проблемы с сайтами", f"Обнаружены проблемы:\n{problems}")
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=f"⚠️ Проблемы с сайтами:\n{problems}"
            )
        
        await asyncio.sleep(300)  # 5 минут

# ===================== ЗАПУСК БОТА =====================
async def main():
    """Основная функция запуска бота"""
    logging.info("Запуск бота...")
    
    try:
        # Создаем приложение
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Регистрируем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # Запускаем фоновую задачу
        asyncio.create_task(background_check(app))
        
        # Запускаем бота
        logging.info("Бот запущен и ожидает сообщений...")
        await app.run_polling()
        
    except Exception as e:
        logging.error(f"Ошибка в main(): {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Явный запуск event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
    finally:
        logging.info("Завершение работы...")
        loop.close()