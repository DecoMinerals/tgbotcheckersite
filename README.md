# Telegram Bot Site Checker

## Установка

1. Клонировать:
```bash
git clone https://github.com/ВАШ_ПОЛЬЗОВАТЕЛЬ/tgbotcheckersite.git
cd tgbotcheckersite
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Вставить токен и chat_id в `index.py`

4. Запустить бота:
```bash
nohup python3 index.py > run.log 2>&1 &
```

5. Проверка логов:
```bash
tail -f bot.log
```