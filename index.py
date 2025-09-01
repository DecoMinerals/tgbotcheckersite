import nest_asyncio
nest_asyncio.apply()

from datetime import datetime
import os
import logging
import requests
import smtplib
import asyncio
import telegram
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# --- Загрузка переменных ---
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')
PASSWORD = os.getenv('PASSBOT')

# --- Список сайтов ---
SITES = [
    "http://sdasdads.ru",
    "https://silmer.org",
    "https://decomachinery.ru",
    "https://decominerals.ru",
    "https://stevent.ru",
    "https://hockey.decominerals.ru",
    "https://decofiltr.ru",
    "https://decomol.ru",
    "https://decoseeds.ru",
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

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

print("✅ Запуск бота...")

# --- Email (основной) ---
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            logging.info(f"📧 Email отправлен на {RECEIVER_EMAIL}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке email: {str(e)}")

# --- Дополнительный email для Timeweb ---
def send_short_email_to_timeweb(problem_sites):
    try:
        short_message = (
            "Здравствуйте, логин нашего аккаунта ct04655. \nЭто автоматическое сообщение при нарушении работы наших сайтов. \n\n"
            "Убедительная просьба решить проблему, возможно откатить резервную копию. \n"
            "Сайт stevent.ru если сломан, то скорее всего он кэширует данные плагинами, можно попробовать их отключить. \n\n"
            "Обнаружены следующие проблемы с сайтами:\n\n" + "\n".join(problem_sites) + "\n\n\nP.S. Извините за возможный СПАМ, я просто в отъезде и поэтому автоматизировал запрос Вам. Пожалуйста, не добавляйте в черный список нас! \n\nКак только проблема решиться сообщения перестанут к Вам приходить!"
        )

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = "info@timeweb.ru"
        msg['Subject'] = "Сайты не работают"
        msg.attach(MIMEText(short_message, 'plain', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            logging.info("📧 Email отправлен на info@timeweb.ru")
            return True

    except Exception as e:
        logging.error(f"❌ Ошибка при отправке email в Timeweb: {str(e)}")
        return False



# --- Авторизация ---
is_authenticated = False

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated:
        await update.message.reply_text(
            r"Пожалуйста\, введите пароль для доступа\." + "\n" +
            r"||Подсказка\: фамилия программиста на английском||",
            parse_mode="MarkdownV2"
        )
    else:
        keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"👋 Привет! Я бот для мониторинга {len(SITES)} сайтов.\n"
            "Нажми кнопку ниже, чтобы проверить статус.",
            reply_markup=reply_markup
        )

# --- Проверка пароля ---
async def password_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_authenticated
    if update.message.text == PASSWORD:
        is_authenticated = True
        await update.message.reply_text("🔓 Пароль верный! Доступ разрешен.")
        await start(update, context)
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова.")

# --- DNS ---
def check_dns(url):
    try:
        domain = urlparse(url).hostname
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

# --- Проверка сайтов ---
def check_sites():
    result = []
    for site in SITES:
        try:
            if not check_dns(site):
                result.append(f"❌ {site} DNS ошибка")
                continue

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html'
            }

            try:
                response = requests.head(site, headers=headers, timeout=15, allow_redirects=True)
                if response.status_code == 405:
                    response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)
            except requests.exceptions.SSLError:
                response = requests.get(site, headers=headers, timeout=15, allow_redirects=True, verify=False)
            except:
                response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)

            if response.status_code == 200:
                result.append(f"✅ {site} работает (код {response.status_code})")
            elif 300 <= response.status_code < 400:
                result.append(f"⚠️ {site} перенаправление (код {response.status_code})")
            elif 400 <= response.status_code < 500:
                result.append(f"❌ {site} клиентская ошибка (код {response.status_code})")
            else:
                result.append(f"❌ {site} серверная ошибка (код {response.status_code})")

        except requests.exceptions.SSLError as e:
            result.append(f"⚠️ {site} ошибка SSL: {str(e)}")
        except requests.exceptions.ConnectionError:
            result.append(f"❌ {site} ошибка подключения")
        # except Exception as e:
        #     result.append(f"❌ {site} непредвиденная ошибка: {str(e)}")

    return result

# --- Email при проблемах ---
def send_email_if_needed(statuses):
    problem_sites = [status for status in statuses if "❌" in status or "⚠️" in status]
    if problem_sites:
        full_message = "⚠️ Обнаружены проблемы с сайтами\n\n" + "\n".join(problem_sites)
        send_email("Проблемы с сайтами", full_message)
        # send_short_email_to_timeweb(problem_sites)

# --- Обработка кнопки ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        if not is_authenticated:
            await query.edit_message_text(
                r"Пожалуйста\, введите пароль для доступа\." + "\n" +
                r"||Подсказка\: фамилия программиста на английском||",
                parse_mode="MarkdownV2"
            )
            return

        await query.edit_message_text("⏳ Проверяю сайты...")
        result = check_sites()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message_lines = [
            f"🔍 Результаты проверки сайтов",
            f"Время: {current_time}\n"
        ] + result

        message = "\n".join(message_lines)

        send_email_if_needed(result)

        if len(message) > 4000:
            message = message[:4000] + "\n\n⚠️ Сообщение обрезано"

        keyboard = [[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e):
            logging.warning("Callback query expired - ignoring")
            return
        raise
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки: {e}")
        raise

# --- Фоновая проверка ---
async def background_check(app):
    logging.info("🔄 Фоновая проверка сайтов запущена")
    while True:
        try:
            result = check_sites()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            problem_sites = [s for s in result if "❌" in s or "⚠️" in s]

            if problem_sites:
                msg = (
                    f"⚠️ Обнаружены проблемы с сайтами\n\n"
                    f"Время проверки: {current_time}\n\n" +
                    "\n".join(problem_sites)
                )

                keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                  f"Нажми кнопку ниже, чтобы проверить статус.",
                reply_markup=reply_markup
        )

                # Отправка уведомлений
                await app.bot.send_message(chat_id=CHAT_ID, text=msg[:4000])

                send_email("Проблемы с сайтами", msg)
                # success = send_short_email_to_timeweb(problem_sites)

                # Telegram-уведомление об отправке email
                if success:
                    await app.bot.send_message(chat_id=CHAT_ID, text="✅ Email отправлен в Timeweb.")
                else:
                    await app.bot.send_message(chat_id=CHAT_ID, text="❌ Не удалось отправить email в Timeweb!")

        except Exception as e:
            logging.error(f"Ошибка в фоновом процессе: {e}")

        await asyncio.sleep(60 * 5)  # Пауза 5 минут



# --- Запуск бота ---
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, password_check))
    application.add_handler(CallbackQueryHandler(button_handler))

    loop = asyncio.get_event_loop()
    loop.create_task(background_check(application))

    application.run_polling()
