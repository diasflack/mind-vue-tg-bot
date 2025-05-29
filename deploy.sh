#!/bin/bash

# Development script for the Telegram Mood Tracker Bot
# Usage: ./dev.sh [start|logs|restart|stop]

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Creating template..."
    echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
    echo "Please edit .env with your actual token"
    exit 1
fi

# Docker Compose file
COMPOSE_FILE="docker-compose.yml"

# Command handling
case "$1" in
    start)
        echo "Starting development environment..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "To view logs: ./deploy.sh logs"
        echo "To run the bot: ./deploy.sh exec"
        ;;
    exec)
        echo "Running the bot in the container..."
        docker-compose -f $COMPOSE_FILE exec mind-vue-bot python main.py
        ;;
    logs)
        echo "Showing logs..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    stop)
        echo "Stopping development environment..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "Restarting bot process..."
        # This restarts just the Python process, not the container
        docker-compose -f $COMPOSE_FILE exec mind-vue-bot pkill -f "python main.py" || true
        echo "To start the bot again: ./dev.sh exec"
        ;;
    rebuild)
        echo "Rebuilding container..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    *)
        echo "Usage: $0 [start|exec|logs|stop|restart|rebuild]"
        echo ""
        echo "  start   - Start development environment"
        echo "  exec    - Run the bot in the container"
        echo "  logs    - Show logs"
        echo "  stop    - Stop development environment"
        echo "  restart - Restart bot process (after code changes)"
        echo "  rebuild - Rebuild container (only needed for dependency changes)"
        exit 1
        ;;
esac

exit 0