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

# --- Список сайтов ---
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

# --- Email отправка --- 
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
            print(f"📧 Email отправлен на {RECEIVER_EMAIL}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке email: {str(e)}")
        raise

# --- Пароль для бота ---
PASSWORD = os.getenv('PASSBOT')
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
    password_input = update.message.text
    if password_input == PASSWORD:
        is_authenticated = True
        await update.message.reply_text("🔓 Пароль верный! Доступ разрешен.")
        await start(update, context)
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова.")

# --- Проверка DNS ---
def check_dns(url):
    try:
        domain = urlparse(url).hostname
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

# --- Проверка сайтов вручную ---
def check_sites():
    result = []
    for site in SITES:
        try:
            if not check_dns(site):
                status = f"❌ {site} DNS ошибка"
                result.append(status)
                continue

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
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
                status = f"✅ {site} работает (код {response.status_code})"
            elif 300 <= response.status_code < 400:
                status = f"⚠️ {site} перенаправление (код {response.status_code})"
            elif 400 <= response.status_code < 500:
                status = f"❌ {site} клиентская ошибка (код {response.status_code})"
            else:
                status = f"❌ {site} серверная ошибка (код {response.status_code})"

        except requests.exceptions.SSLError as e:
            status = f"⚠️ {site} ошибка SSL: {str(e)}"
        except requests.exceptions.Timeout:
            status = f"⚠️ {site} таймаут соединения"
        except requests.exceptions.ConnectionError:
            status = f"❌ {site} ошибка подключения"
        except requests.exceptions.RequestException as e:
            status = f"❌ {site} ошибка запроса: {str(e)}"
        except Exception as e:
            status = f"❌ {site} непредвиденная ошибка: {str(e)}"
            
        logging.info(f"{site} — {status}")
        result.append(status)
    return result

# --- Email отправка только при ошибках ---
def send_email_if_needed(statuses):
    problem_sites = [status for status in statuses if "❌" in status or "⚠️" in status]
    if problem_sites:
        message = (
            f"⚠️ Обнаружены проблемы с сайтами\n\n"
            f"{'\n'.join(problem_sites)}"
        )
        send_email("Проблемы с сайтами", message)

# --- Обработка кнопки (принудительная проверка) ---
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

        # Если есть проблемы с сайтами, отправляем только их
        problem_sites = [status for status in result if "❌" in status or "⚠️" in status]

        if problem_sites:
            message = (
                f"⚠️ Обнаружены проблемы с сайтами\n\n"
                f"Время проверки: {current_time}\n\n"
                f"{'\n'.join(problem_sites)}"
            )

            send_email_if_needed(result)
        else:
            message = (
                f"✅ Все сайты работают корректно\n\n"
                f"Время проверки: {current_time}\n"
                "Все сайты работают без ошибок!"
            )

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
    global status_cache
    logging.info("🔄 Фоновая проверка сайтов запущена")

    while True:
        try:
            logging.info("🔍 Начинаю новую проверку сайтов...")
            current_status = {}

            for site in SITES:
                try:
                    if not check_dns(site):
                        current_status[site] = "❌ DNS ошибка"
                        continue

                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }

                    try:
                        response = requests.head(site, headers=headers, timeout=20, allow_redirects=True)
                        if response.status_code == 405:
                            response = requests.get(site, headers=headers, timeout=20, allow_redirects=True)
                    except requests.exceptions.SSLError:
                        response = requests.get(site, headers=headers, timeout=20, allow_redirects=True, verify=False)
                    except:
                        response = requests.get(site, headers=headers, timeout=20, allow_redirects=True)

                    if response.status_code == 200:
                        current_status[site] = f"✅ {site} работает (код {response.status_code})"
                    elif 300 <= response.status_code < 400:
                        current_status[site] = f"⚠️ {site} перенаправление ({response.status_code})"
                    elif 400 <= response.status_code < 500:
                        current_status[site] = f"❌ {site} клиентская ошибка ({response.status_code})"
                    else:
                        current_status[site] = f"❌ {site} серверная ошибка ({response.status_code})"

                except requests.exceptions.SSLError:
                    current_status[site] = f"⚠️ {site} ошибка SSL"
                except requests.exceptions.Timeout:
                    current_status[site] = f"⚠️ {site} таймаут"
                except requests.exceptions.ConnectionError:
                    current_status[site] = f"❌ {site} ошибка подключения"
                except Exception as e:
                    current_status[site] = f"❌ {site} ошибка: {str(e)}"

                logging.info(f"Проверен {site}: {current_status[site]}")
                await asyncio.sleep(1)

            problem_sites = [
                f"{site} — {status}" 
                for site, status in current_status.items() 
                if "❌" in status or "⚠️" in status
            ]

            if problem_sites:
                msg = (
                    f"⚠️ Обнаружены проблемы с сайтами\n\n"
                    f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" +
                    "\n".join(problem_sites)
                )
                try:
                    await app.bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg[:4000],
                        disable_notification=False
                    )
                    logging.info("Уведомление о проблемах отправлено")
                    send_email("Проблемы с сайтами", msg)
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления: {e}")
            else:
                msg = (
                    f"✅ Все сайты работают корректно\n\n"
                    f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "Все сайты работают без ошибок!"
                )
                try:
                    await app.bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg[:4000],
                        disable_notification=True
                    )
                    logging.info("Уведомление о нормальном состоянии отправлено")
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления: {e}")
        except Exception as e:
            logging.error(f"Ошибка в фоновом процессе: {e}")
            await asyncio.sleep(60)

        await asyncio.sleep(60 * 5)  # Проверка каждые 5 минут

# --- Главный блок ---
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, password_check))
    application.add_handler(CallbackQueryHandler(button_handler))

    loop = asyncio.get_event_loop()
    loop.create_task(background_check(application))

    application.run_polling()
