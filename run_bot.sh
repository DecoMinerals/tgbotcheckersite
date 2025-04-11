#!/bin/bash

# Переменные
LOG_FILE="bot.log"
PID_FILE="bot.pid"
VENV_PATH="venv"  # Путь к виртуальному окружению, если используешь
PYTHON_BIN="$VENV_PATH/bin/python"  # Путь к интерпретатору Python из виртуального окружения
BOT_SCRIPT="bot.py"  # Имя скрипта с ботом

# Проверка, запущен ли уже бот
if [ -f "$PID_FILE" ]; then
    echo "❌ Бот уже запущен. PID файл существует: $(cat $PID_FILE)"
    exit 1
fi

# Запуск бота
echo "🚀 Запуск бота..."
nohup $PYTHON_BIN $BOT_SCRIPT >> $LOG_FILE 2>&1 &

# Получение PID процесса и запись в файл
echo $! > "$PID_FILE"

echo "✅ Бот запущен, логи записываются в $LOG_FILE"

# Функция для остановки бота
trap "echo '🛑 Остановка бота...'; kill $(cat $PID_FILE); rm -f $PID_FILE; exit" SIGINT SIGTERM
