import requests
import time
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from datetime import datetime

# Токен бота, который вы получили от BotFather
TELEGRAM_TOKEN = '7487235916:AAFijvFJ_n1ip-EckW7jr1rFYqgZsDX7EGc'
# Ваш Telegram chat_id. Чтобы его получить, напишите боту /start и используйте метод getUpdates
CHAT_ID = '1911443016'

# Список сайтов для проверки
SITES = [
    "https://stevent.ru",
    "https://decominerals.ru",
    # Добавьте сюда нужные сайты
]

# Функция проверки сайтов
def check_sites():
    for site in SITES:
        try:
            response = requests.get(site, timeout=10)
            if response.status_code != 200:
                send_message(f"Сайт {site} вернул код ошибки {response.status_code}")
        except requests.exceptions.RequestException as e:
            send_message(f"Ошибка при проверке {site}: {str(e)}")

# Функция отправки сообщения в Telegram
def send_message(message):
    bot = Bot(TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=message)

# Основная функция, которая будет запускаться по расписанию
def check_sites_periodically():
    while True:
        check_sites()
        time.sleep(300)  # Проверка каждые 5 минут

if __name__ == '__main__':
    check_sites_periodically()
