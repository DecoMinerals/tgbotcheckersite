import nest_asyncio
nest_asyncio.apply()

from datetime import datetime
import os
import logging
import requests
import smtplib
import asyncio
import telegram
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
    "https://rfrp36.ru/"
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
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

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

# --- Команда /ping ---
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Бот работает!")

# --- Проверка сайтов вручную ---
def check_sites():
    result = []
    for site in SITES:
        try:
            # Добавляем заголовки, чтобы выглядеть как обычный браузер
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            
            # Проверяем как HEAD запросом (быстрее), если не получается - GET
            try:
                response = requests.head(site, headers=headers, timeout=10, allow_redirects=True)
                # Если HEAD не поддерживается, пробуем GET
                if response.status_code == 405:
                    response = requests.get(site, headers=headers, timeout=10, allow_redirects=True)
            except:
                response = requests.get(site, headers=headers, timeout=10, allow_redirects=True)
            
            # Проверяем статус код и содержимое ответа
            if response.status_code == 200:
                # Дополнительная проверка для некоторых сайтов
                if 'decopure.ru' in site and len(response.content) < 500:
                    status = f"⚠️ {site} подозрительно маленький ответ ({len(response.content)} байт)"
                else:
                    status = f"✅ {site} работает (код {response.status_code})"
            elif 300 <= response.status_code < 400:
                status = f"⚠️ {site} перенаправление (код {response.status_code})"
            else:
                status = f"❌ {site} код ошибки: {response.status_code}"
                
        except requests.exceptions.SSLError as e:
            status = f"⚠️ {site} ошибка SSL: {str(e)}"
        except requests.exceptions.Timeout:
            status = f"⚠️ {site} таймаут соединения"
        except requests.exceptions.ConnectionError:
            status = f"⚠️ {site} ошибка подключения"
        except requests.exceptions.RequestException as e:
            status = f"❌ {site} ошибка запроса: {str(e)}"
        except Exception as e:
            status = f"❌ {site} непредвиденная ошибка: {str(e)}"
            
        logging.info(f"{site} — {status}")
        result.append(status)
    return result

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
        all_sites = "\n".join(result)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"🔍 Все проверенные сайты:\n\n{all_sites}\n\n"
            f"📅 Дата и время проверки: {current_time}"
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

# --- Проверка Telegram API ---
async def health_check(app):
    while True:
        try:
            await app.bot.get_me()
            logging.info("✅ Бот жив и отвечает Telegram API")
        except Exception as e:
            logging.error(f"❌ Telegram API недоступен: {e}")
            try:
                await app.bot.send_message(chat_id=CHAT_ID, text="🚨 Проблема с Telegram API!")
            except Exception:
                pass
            try:
                send_email("🚨 Бот недоступен", f"Ошибка: {e}")
            except Exception:
                logging.error("❌ Не удалось отправить email о сбое бота")
        await asyncio.sleep(600)

# --- Кэш статусов ---
status_cache = {}

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
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    # Пробуем HEAD запрос сначала
                    try:
                        response = requests.head(site, headers=headers, timeout=15, allow_redirects=True)
                        if response.status_code == 405:  # HEAD не поддерживается
                            response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)
                    except:
                        response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)
                    
                    # Более точная проверка статуса
                    if response.status_code == 200:
                        if 'decopure.ru' in site and len(response.content) < 500:
                            current_status[site] = f"⚠️ Маленький ответ ({len(response.content)} байт)"
                        else:
                            current_status[site] = "✅"
                    elif 300 <= response.status_code < 400:
                        current_status[site] = f"⚠️ Перенаправление ({response.status_code})"
                    elif 400 <= response.status_code < 500:
                        current_status[site] = f"⚠️ Клиентская ошибка ({response.status_code})"
                    else:
                        current_status[site] = f"❌ Серверная ошибка ({response.status_code})"
                        
                except requests.exceptions.SSLError:
                    current_status[site] = "⚠️ Ошибка SSL"
                except requests.exceptions.Timeout:
                    current_status[site] = "⚠️ Таймаут"
                except requests.exceptions.ConnectionError:
                    current_status[site] = "⚠️ Ошибка подключения"
                except Exception as e:
                    current_status[site] = f"❌ Ошибка: {str(e)}"
                
                logging.info(f"Проверен {site}: {current_status[site]}")
                await asyncio.sleep(1)  # Пауза между запросами

# --- Запуск ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password_check))

    # Создаем и запускаем фоновые задачи
    bg_check_task = asyncio.create_task(background_check(app))
    health_task = asyncio.create_task(health_check(app))

    logging.info("🚀 Бот запущен")
    
    try:
        await app.run_polling()
    finally:
        # Корректное завершение фоновых задач
        bg_check_task.cancel()
        health_task.cancel()
        try:
            await bg_check_task
            await health_task
        except asyncio.CancelledError:
            logging.info("Фоновые задачи корректно завершены")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлен пользователем")
    except Exception as e:
        logging.error(f"❌ Ошибка запуска: {e}")
        print(f"❌ Ошибка запуска: {e}")