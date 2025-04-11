# --- ВЕРХНЯЯ ЧАСТЬ НЕ МЕНЯЛАСЬ ---
import nest_asyncio
nest_asyncio.apply()

from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import requests
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Загрузка переменных
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
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
    "https://rfrp36.ru/"
]

# Логирование
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
print("✅ Запуск бота...")

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

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
        logging.info(f"Email отправлен: {subject}")
    except Exception as e:
        logging.error(f"Ошибка при отправке email: {e}")

async def check_site(site):
    try:
        response = requests.get(site, timeout=10)
        if response.status_code == 200:
            return "ok"
        return f"warn ({response.status_code})"
    except requests.exceptions.RequestException:
        return "fail"

async def double_check_site(site):
    status1 = await check_site(site)
    if status1 == "ok":
        return status1
    await asyncio.sleep(3)
    return await check_site(site)

# Текущее состояние сайтов
site_statuses = {site: "unknown" for site in SITES}

# --- ОБРАБОТЧИКИ КОМАНД ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Проверить сайты", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет! Я мониторю {len(SITES)} сайтов.\n"
        "Нажми кнопку ниже, чтобы проверить статус.",
        reply_markup=reply_markup
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Бот работает!")

# --- ПРОВЕРКА САЙТОВ ---

async def perform_check(app, is_manual=False):
    global site_statuses
    message_lines = []
    restored_sites = []
    failed_sites = []
    warned_sites = []

    for site in SITES:
        new_status = await double_check_site(site)
        old_status = site_statuses.get(site, "unknown")

        # Определяем статус для вывода
        if new_status == "ok":
            status_text = "✅ работает"
        elif "warn" in new_status:
            status_text = f"⚠️ ошибка: код {new_status.split()[-1]}"
        else:
            status_text = "❌ сайт недоступен"

        # Восстановление
        if old_status != "ok" and new_status == "ok":
            restored_sites.append(site)

        # Сбор проблем
        if new_status == "fail":
            failed_sites.append(f"{site} — {status_text}")
        elif "warn" in new_status:
            warned_sites.append(f"{site} — {status_text}")

        # Обновляем статус
        site_statuses[site] = new_status
        message_lines.append(f"{site} — {status_text}")

    # Суммарная шапка
    summary = f"🔍 Проверено {len(SITES)} сайтов\n"
    summary += f"❗ Критических: {len(failed_sites)} | Предупреждений: {len(warned_sites)}\n"

    # Решаем, что показывать
    if failed_sites or warned_sites:
        details = "\n".join(failed_sites + warned_sites)
    else:
        details = "\n".join(message_lines)

    # Ограничение длины
    if len(details) > 3800:
        details = details[:3800] + "\n\n⚠️ Сообщение обрезано из-за лимита Telegram"

    # Добавляем кнопку
    keyboard = [[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    final_message = summary + "\n\n" + details

    if is_manual:
        await app.bot.send_message(chat_id=CHAT_ID, text=final_message, reply_markup=reply_markup)
    else:
        if failed_sites:
            await app.bot.send_message(chat_id=CHAT_ID, text=final_message, reply_markup=reply_markup, disable_notification=False)
            send_email("❌ Критические сбои сайтов", final_message)
        elif warned_sites:
            await app.bot.send_message(chat_id=CHAT_ID, text=final_message, reply_markup=reply_markup, disable_notification=True)
            send_email("⚠️ Предупреждения по сайтам", final_message)

    # Уведомление о восстановлении
    if restored_sites:
        restored_text = "🟢 Сайты восстановлены:\n" + "\n".join(restored_sites)
        await app.bot.send_message(chat_id=CHAT_ID, text=restored_text, disable_notification=True)
        logging.info(f"Сайты восстановлены: {restored_sites}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Идёт проверка, пожалуйста подождите...")
    await perform_check(context.application, is_manual=True)

async def background_check(app):
    while True:
        await perform_check(app)
        await asyncio.sleep(60)

async def health_check(app):
    while True:
        try:
            await app.bot.get_me()
            logging.info("✅ Health check: бот работает")
        except Exception as e:
            msg = f"❌ Бот не отвечает: {e}"
            logging.error(msg)
            try:
                await app.bot.send_message(chat_id=CHAT_ID, text=msg)
                send_email("🚨 Бот не отвечает", msg)
            except:
                pass
        await asyncio.sleep(600)

# --- ОСНОВНОЙ ЗАПУСК ---

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(background_check(app))
    asyncio.create_task(health_check(app))
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка запуска: {e}")
