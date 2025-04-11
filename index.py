import nest_asyncio
nest_asyncio.apply()

from datetime import datetime
import os
import logging
import requests
import smtplib
import asyncio
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
        raise  # пробрасываем ошибку для обработки выше

# --- Пароль для бота ---
PASSWORD = os.getenv('PASSBOT')
is_authenticated = False

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated:
        await update.message.reply_text("Введите пароль для доступа к боту. Подсказка: фамилия программиста")
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
        await start(update, context)  # Перезапуск /start после успешной аутентификации
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
            response = requests.get(site, timeout=10)
            if response.status_code == 200:
                status = f"✅ {site} работает"
            else:
                status = f"⚠️ {site} код ошибки: {response.status_code}"
            logging.info(f"{site} — {status}")
        except requests.exceptions.RequestException as e:
            status = f"❌ {site} ошибка: {e}"
            logging.error(f"{site} — {status}")
        result.append(status)
    return result

# --- Обработка кнопки ---
# --- Проверка на аутентификацию перед показом проблем ---
# --- Обработка кнопки ---
# --- Обработка кнопки ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated:
        await update.message.reply_text(
    "❌ Пожалуйста, введите пароль для доступа. ||Подсказка: фамилия программиста на английском||",
    parse_mode="MarkdownV2"
        )
        return

    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Проверяю сайты...")

    result = check_sites()

    # Все сайты с их статусом
    all_sites = "\n".join(result)

    # Получаем текущую дату и время
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Сообщение, которое будет отправлено
    message = (
        f"🔍 Все проверенные сайты:\n\n{all_sites}\n\n"
        f"📅 Дата и время проверки: {current_time}"
    )

    # Если сообщение слишком длинное, его обрезаем
    if len(message) > 4000:
        message = message[:4000] + "\n\n⚠️ Сообщение обрезано"

    # Кнопка для повторной проверки
    keyboard = [[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)



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

    while True:
        logging.info("🌐 Фоновая проверка сайтов...")
        current_status = {}

        for site in SITES:
            try:
                response = requests.get(site, timeout=10)
                if response.status_code == 200:
                    current_status[site] = "✅"
                elif response.status_code >= 500:
                    current_status[site] = f"❌ {response.status_code}"  # Добавлен код ошибки
                else:
                    current_status[site] = f"⚠️ {response.status_code}"  # Добавлен код ошибки
            except Exception as e:
                current_status[site] = f"❌ Ошибка: {str(e)}"  # Добавлен текст ошибки

        # Найдём проблемы
        problem_sites = [f"{site} — {current_status[site]}" for site in current_status if current_status[site] in ("❌", "⚠️")]

        # Найдём восстановленные
        recovered_sites = [
            site for site in current_status
            if status_cache.get(site) in ("❌", "⚠️") and current_status[site] == "✅"
        ]

        # Обновляем кэш
        status_cache = current_status.copy()

        # Уведомление о проблемах
        if problem_sites:
            if is_authenticated:
                msg = (
                    f"⚠️ Обнаружены проблемы:\n"
                    f"Это автоматическое сообщение от: \n"
                    f"🕓 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" +
                    "\n".join(problem_sites)
                )

                try:
                    logging.info(f"📬 Отправка сообщения с проблемами: {msg}")
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
                    send_email("❗ Проблемы с сайтами", msg)
                except Exception as e:
                    error_msg = f"❌ Ошибка при отправке сообщения: {e}"
                    logging.error(error_msg)
                    await app.bot.send_message(chat_id=CHAT_ID, text=error_msg)

                    # Письмо не отправлено — добавим ошибку логирования
                    try:
                        send_email("❗ Ошибка отправки email", error_msg)
                    except Exception as email_error:
                        logging.error(f"❌ Ошибка при отправке email о проблемах: {email_error}")
            else:
                logging.info("🔒 Проблемы с сайтами, но сообщение не отправлено — пользователь не авторизован")

        # Уведомление о восстановлении (без звука)
        if recovered_sites:
            if is_authenticated:
                msg = f"✅ Восстановились:\n" + "\n".join(recovered_sites)
                logging.info(f"📬 Отправка сообщения о восстановлении: {msg}")
                await app.bot.send_message(chat_id=CHAT_ID, text=msg, disable_notification=True)
            else:
                logging.info("🔒 Восстановленные сайты, но сообщение не отправлено — пользователь не авторизован")

        await asyncio.sleep(60)

# --- Запуск ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик для ввода пароля
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password_check))

    asyncio.create_task(background_check(app))
    asyncio.create_task(health_check(app))

    logging.info("🚀 Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлен пользователем")
    except Exception as e:
        logging.error(f"❌ Ошибка запуска: {e}")
        print(f"❌ Ошибка запуска: {e}")
