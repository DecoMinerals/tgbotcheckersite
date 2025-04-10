import nest_asyncio
nest_asyncio.apply()

import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

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
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Настройки почты
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')

SITES = [
    "https://decominerals.ru",
    "https://stevent.ru",
    "https://stevent.ru/информация",
    "https://hockey.decominerals.ru",
    "https://decofiltr.ru",
    "https://decomol.ru",
    "https://decoseeds.ru",
    "https://halofiltr.ru",
    "https://benteco.ru",
    "https://amitox.ru",
    "https://decoguard.ru",
    "https://decofield.pro",
    "https://decoorb.ru",
    "https://decoclear.ru",
    "https://decoarmor.ru",
    "https://decopool.pro",
    "https://decobase.pro",
    "https://decoessence.ru",
    "https://decobrew.ru",
    "https://decogrape.ru",
    "https://decopure.ru",
    "https://decoaqua.ru",
    "https://decobrights.ru",
    "https://stilldry.pro",
    "https://roaddry.ru",
    "https://decocopper.pro",
    "https://decotech.pro",
    "https://decofry.ru",
]

# Логирование
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

print("✅ Запуск бота...")

def send_email(subject, body):
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

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_sites = len(SITES)
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет! Я бот для мониторинга {total_sites} сайтов.\n"
        "Нажми кнопку ниже, чтобы проверить статус.",
        reply_markup=reply_markup
    )
    print("📩 Получена команда /start")

# Команда /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Бот работает!")
    print("🏓 Получена команда /ping")

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Сообщаем пользователю, что бот начал проверку
    await query.edit_message_text("⏳ Проверяю сайты... Пожалуйста, подождите.")

    await asyncio.sleep(1)  # Небольшая задержка, чтобы показать "думаю..."

    # Получаем список сайтов и начинаем проверку
    total_sites = len(SITES)
    result = check_sites()  # Проверка всех сайтов
    problem_sites = [r for r in result if "❌" in r or "⚠️" in r]  # Проблемные сайты
    problem_count = len(problem_sites)

    # Создаем клавиатуру с кнопкой "Проверить снова"
    keyboard = [[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Формируем сообщение с результатами
    message = (
        f"🔍 Проверено {total_sites} сайтов\n"
        f"❗ Проблемных: {problem_count}\n\n" +
        "\n".join(result)
    )

    # Если сообщение слишком длинное, обрезаем его
    if len(message) > 4000:
        message = message[:4000] + "\n\n⚠️ Сообщение обрезано из-за лимита Telegram"

    # Отправляем результаты обратно в Telegram
    await query.edit_message_text(message, reply_markup=reply_markup)

    # Логируем информацию в консоль
    print(f"✅ Проверка завершена: {total_sites} сайтов проверено, {problem_count} с проблемами.")


    """Периодически проверяет, жив ли бот и может ли обращаться к Telegram API"""
async def health_check(app):
    """Периодически проверяет, жив ли бот и может ли обращаться к Telegram API"""
    while True:
        try:
            await app.bot.get_me()
            print("✅ Бот жив и отвечает Telegram API")
            logging.info("Health check: бот работает нормально")
        except Exception as e:
            error_message = f"❌ Бот не отвечает: {e}"
            print(error_message)
            logging.error(f"Health check failed: {e}")

            # Отправка уведомления в Telegram
            try:
                await app.bot.send_message(
                    chat_id=CHAT_ID,
                    text="🚨 Бот не отвечает Telegram API!\nПроверь сервер или соединение."
                )
            except Exception as tg_error:
                logging.error(f"Не удалось отправить сообщение в Telegram: {tg_error}")

            # Отправка уведомления на email
            try:
                send_email(
                    subject="🚨 Ошибка бота Telegram",
                    body=f"Бот не отвечает: {e}"
                )
            except Exception as email_error:
                logging.error(f"Не удалось отправить email: {email_error}")

        await asyncio.sleep(600)  # Проверка каждые 5 минут



# Фоновая проверка
async def background_check(app):
    while True:
        logging.info("Фоновая проверка сайтов")
        result = check_sites()
        problem_sites = [r for r in result if "❌" in r or "⚠️" in r]

        if problem_sites:
            total_sites = len(SITES)
            problem_count = len(problem_sites)

            problems = (
    f"⚠️ Обнаружены проблемы с сайтами ({problem_count}/{total_sites}):\n"
    f"🕓 Это автоматическое сообщение от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" +
    "\n".join(problem_sites)
)


            keyboard = [[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=problems[:4000],
                reply_markup=reply_markup
            )

            send_email("Проблемы с сайтами", problems)

        await asyncio.sleep(60)

# Основной запуск
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Фоновые задачи
    asyncio.create_task(background_check(app))
    asyncio.create_task(health_check(app))
    print("✅ Бот запущен и слушает Telegram API")

    logging.info("Бот запущен")
    print("🚀 Бот запущен и готов к работе!")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
        print("🛑 Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")
        print(f"❌ Ошибка при запуске: {e}")
