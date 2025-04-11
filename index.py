import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging
import asyncio
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# Список сайтов для проверки
SITES = [
    'https://decominerals.ru',
    'https://stevent.ru',
    'https://stevent.ru/информация',
    'https://hockey.decominerals.ru',
    'https://decofiltr.ru',
    'https://decomol.ru',
    'https://decoseeds.ru',
    'https://halofiltr.ru'
]

# Параметры для отправки Email
SENDER_EMAIL = 'your-email@example.com'
RECEIVER_EMAIL = 'receiver-email@example.com'
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
SENDER_PASSWORD = 'your-email-password'

# Логирование
logging.basicConfig(level=logging.INFO)

# Функция для проверки DNS сайта
def check_dns(site):
    try:
        requests.get(site, timeout=5)
        return True
    except requests.exceptions.RequestException:
        return False

# --- Проверка сайтов вручную ---
def check_sites():
    result = []
    for site in SITES:
        try:
            # Проверка DNS перед запросом
            if not check_dns(site):
                status = f"❌ {site} DNS ошибка"
                result.append(status)
                continue

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            try:
                # Сначала пробуем HEAD запрос
                response = requests.head(site, headers=headers, timeout=15, allow_redirects=True)
                if response.status_code == 405:  # Если метод HEAD не поддерживается
                    response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)
            except requests.exceptions.SSLError:
                # Если SSL ошибка, пробуем без верификации
                response = requests.get(site, headers=headers, timeout=15, allow_redirects=True, verify=False)
            except:
                response = requests.get(site, headers=headers, timeout=15, allow_redirects=True)

            # Анализ ответа
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
        all_sites = "\n".join(result)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Если есть проблемы с сайтами, отправляем только их
        problem_sites = [status for status in result if "❌" in status or "⚠️" in status]

        if problem_sites:
            message = (
                f"⚠️ Обнаружены проблемы с сайтами\n\n"
                f"Время проверки: {current_time}\n\n"
                f"{'\n'.join(problem_sites)}"
            )

            # Отправляем Email только если есть ошибки
            send_email("Проблемы с сайтами", message)
        else:
            message = (
                f"✅ Все сайты работают корректно\n\n"
                f"Время проверки: {current_time}\n"
                "Все сайты работают без ошибок!"
            )

        # Если сообщение слишком длинное, обрезаем его
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


# --- Фоновая проверка (автоматическая проверка) ---
async def background_check(app):
    global status_cache
    logging.info("🔄 Фоновая проверка сайтов запущена")

    while True:
        try:
            logging.info("🔍 Начинаю новую проверку сайтов...")
            current_status = {}

            for site in SITES:
                try:
                    # Проверка DNS
                    if not check_dns(site):
                        current_status[site] = "❌ DNS ошибка"
                        continue

                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }

                    # Пробуем HEAD запрос сначала
                    try:
                        response = requests.head(site, headers=headers, timeout=20, allow_redirects=True)
                        if response.status_code == 405:  # HEAD не поддерживается
                            response = requests.get(site, headers=headers, timeout=20, allow_redirects=True)
                    except requests.exceptions.SSLError:
                        response = requests.get(site, headers=headers, timeout=20, allow_redirects=True, verify=False)
                    except:
                        response = requests.get(site, headers=headers, timeout=20, allow_redirects=True)

                    # Анализ ответа
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
                await asyncio.sleep(1)  # Пауза между запросами

            # Проверка изменений статуса
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
                # Все сайты работают нормально
                msg = (
                    f"✅ Все сайты работают корректно\n\n"
                    f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "Все сайты работают без ошибок!"
                )
                try:
                    await app.bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg[:4000],
                        disable_notification=True  # Без звукового уведомления
                    )
                    logging.info("Уведомление о нормальной работе сайтов отправлено")
                    send_email("Все сайты работают корректно", msg)
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления: {e}")
                
        except Exception as e:
            logging.error(f"Ошибка в фоновом процессе проверки: {str(e)}")
        await asyncio.sleep(60)  # Пауза перед следующей проверкой
