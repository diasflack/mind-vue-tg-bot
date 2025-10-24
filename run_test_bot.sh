#!/bin/bash
#
# Скрипт для запуска тестового бота Telegram Mood Tracker
#
# Использование:
#   export TEST_BOT_TOKEN="your_test_token_here"
#   ./run_test_bot.sh start
#
#   или
#
#   ./run_test_bot.sh start your_test_token_here
#

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Файлы для управления процессом
PID_FILE="/tmp/mood_tracker_test_bot.pid"
LOG_FILE="/tmp/mood_tracker_test_bot.log"
ENV_FILE=".env.test"

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Telegram Mood Tracker - Тестовое окружение${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

check_bot_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

start_bot() {
    print_header

    if check_bot_running; then
        print_warning "Тестовый бот уже запущен (PID: $(cat $PID_FILE))"
        print_info "Используйте './run_test_bot.sh logs' для просмотра логов"
        print_info "Используйте './run_test_bot.sh restart' для перезапуска"
        exit 1
    fi

    # Получение токена
    if [ -n "$1" ]; then
        BOT_TOKEN="$1"
        print_info "Токен получен из аргумента командной строки"
    elif [ -n "$TEST_BOT_TOKEN" ]; then
        BOT_TOKEN="$TEST_BOT_TOKEN"
        print_info "Токен получен из переменной окружения TEST_BOT_TOKEN"
    elif [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
        BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
        print_info "Токен получен из файла $ENV_FILE"
    else
        print_error "Токен бота не найден!"
        echo ""
        echo "Используйте один из способов:"
        echo "  1. export TEST_BOT_TOKEN=\"your_token\" && ./run_test_bot.sh start"
        echo "  2. ./run_test_bot.sh start your_token"
        echo "  3. Создайте файл .env.test с TELEGRAM_BOT_TOKEN=your_token"
        echo ""
        exit 1
    fi

    # Валидация токена
    if [ -z "$BOT_TOKEN" ]; then
        print_error "Токен бота пустой!"
        exit 1
    fi

    # Создаем временный .env файл для этой сессии
    print_info "Создание временного файла конфигурации..."
    export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"

    # Проверка зависимостей
    print_info "Проверка зависимостей Python..."
    if ! python3 -c "import telegram" 2>/dev/null; then
        print_error "Модуль python-telegram-bot не установлен!"
        print_info "Установите: pip install -r requirements.txt"
        exit 1
    fi

    # Очистка старых логов (оставляем только последние 100 строк если файл существует)
    if [ -f "$LOG_FILE" ]; then
        tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi

    print_success "Конфигурация готова"
    print_info "Запуск тестового бота..."
    echo ""

    # Запуск бота в фоновом режиме
    nohup python3 main.py > "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"

    # Ждем пару секунд и проверяем что бот запустился
    sleep 2

    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        print_success "Тестовый бот запущен успешно!"
        echo ""
        print_info "PID: $BOT_PID"
        print_info "Логи: $LOG_FILE"
        echo ""
        print_success "Бот готов к тестированию в Telegram!"
        echo ""
        echo "Полезные команды:"
        echo "  ./run_test_bot.sh logs     - просмотр логов"
        echo "  ./run_test_bot.sh status   - статус бота"
        echo "  ./run_test_bot.sh stop     - остановить бота"
        echo "  ./run_test_bot.sh restart  - перезапустить бота"
        echo ""

        # Показываем последние строки лога
        print_info "Последние сообщения из лога:"
        echo "─────────────────────────────────────────────────────"
        tail -n 10 "$LOG_FILE"
        echo "─────────────────────────────────────────────────────"
    else
        print_error "Не удалось запустить бота!"
        print_info "Проверьте логи: cat $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_bot() {
    print_header

    if ! check_bot_running; then
        print_warning "Тестовый бот не запущен"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    print_info "Остановка бота (PID: $PID)..."

    kill "$PID" 2>/dev/null || true

    # Ждем до 5 секунд пока процесс завершится
    for i in {1..5}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # Если процесс все еще работает, убиваем принудительно
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warning "Процесс не завершился, принудительная остановка..."
        kill -9 "$PID" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    print_success "Тестовый бот остановлен"
}

show_status() {
    print_header

    if check_bot_running; then
        PID=$(cat "$PID_FILE")
        print_success "Тестовый бот работает (PID: $PID)"

        # Показываем информацию о процессе
        echo ""
        print_info "Информация о процессе:"
        ps -p "$PID" -o pid,pcpu,pmem,etime,cmd | tail -n +2

        echo ""
        print_info "Логи: $LOG_FILE"
        print_info "Используйте './run_test_bot.sh logs' для просмотра логов"
    else
        print_warning "Тестовый бот не запущен"
        print_info "Используйте './run_test_bot.sh start' для запуска"
    fi
}

show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "Файл логов не найден: $LOG_FILE"
        exit 1
    fi

    print_header
    print_info "Логи тестового бота (последние 50 строк):"
    echo "─────────────────────────────────────────────────────"
    tail -n 50 "$LOG_FILE"
    echo "─────────────────────────────────────────────────────"
    echo ""
    print_info "Для просмотра логов в реальном времени: tail -f $LOG_FILE"
}

follow_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "Файл логов не найден: $LOG_FILE"
        exit 1
    fi

    print_header
    print_info "Логи в реальном времени (Ctrl+C для выхода):"
    echo "─────────────────────────────────────────────────────"
    tail -f "$LOG_FILE"
}

restart_bot() {
    print_header
    print_info "Перезапуск тестового бота..."

    if check_bot_running; then
        stop_bot
        sleep 1
    fi

    # Передаем токен из environment если он есть
    if [ -n "$TEST_BOT_TOKEN" ]; then
        start_bot "$TEST_BOT_TOKEN"
    else
        start_bot
    fi
}

show_help() {
    print_header

    echo "Использование: ./run_test_bot.sh COMMAND [OPTIONS]"
    echo ""
    echo "Команды:"
    echo "  start [TOKEN]   - Запустить тестового бота"
    echo "  stop            - Остановить тестового бота"
    echo "  restart         - Перезапустить тестового бота"
    echo "  status          - Показать статус бота"
    echo "  logs            - Показать логи (последние 50 строк)"
    echo "  follow          - Показать логи в реальном времени"
    echo "  help            - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  # Запуск с токеном из переменной окружения"
    echo "  export TEST_BOT_TOKEN=\"123456:ABC-DEF...\""
    echo "  ./run_test_bot.sh start"
    echo ""
    echo "  # Запуск с токеном из аргумента"
    echo "  ./run_test_bot.sh start \"123456:ABC-DEF...\""
    echo ""
    echo "  # Запуск с токеном из .env.test файла"
    echo "  echo 'TELEGRAM_BOT_TOKEN=123456:ABC-DEF...' > .env.test"
    echo "  ./run_test_bot.sh start"
    echo ""
    echo "  # Просмотр статуса"
    echo "  ./run_test_bot.sh status"
    echo ""
    echo "  # Просмотр логов в реальном времени"
    echo "  ./run_test_bot.sh follow"
    echo ""
}

# Main
case "${1:-help}" in
    start)
        start_bot "$2"
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
