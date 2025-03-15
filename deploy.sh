#!/bin/bash

# Simple deployment script for the Telegram Mood Tracker Bot
# Usage: ./deploy.sh [build|run|logs|stop|start|restart]

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it with your TELEGRAM_BOT_TOKEN."
    echo "Example: echo 'TELEGRAM_BOT_TOKEN=your_token_here' > .env"
    exit 1
fi

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN is not set in .env file."
    exit 1
fi

# Docker image name
IMAGE_NAME="mind-vue-bot"
CONTAINER_NAME="mind-vue-bot"

# Command handling
case "$1" in
    build)
        echo "Building Docker image..."
        docker build --no-cache -t $IMAGE_NAME .
        ;;
    run)
        echo "Running container..."
        # Stop and remove existing container if it exists
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true

        # Create data directory if it doesn't exist
        mkdir -p "$(pwd)/user_data"

        # Run new container
        docker run -d \
            --name $CONTAINER_NAME \
            -e TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
            -v "$(pwd)/user_data:/app/user_data" \
            --restart unless-stopped \
            $IMAGE_NAME
        ;;
    logs)
        echo "Showing logs..."
        docker logs -f $CONTAINER_NAME
        ;;
    stop)
        echo "Stopping container..."
        docker stop $CONTAINER_NAME
        ;;
    start)
        echo "Starting container..."
        docker start $CONTAINER_NAME
        ;;
    restart)
        echo "Restarting container..."
        docker restart $CONTAINER_NAME
        ;;
    deploy)
        echo "Full deployment: build and run..."
        $0 build && $0 run
        ;;
    *)
        echo "Usage: $0 [build|run|logs|stop|start|restart|deploy]"
        echo ""
        echo "  build   - Build the Docker image"
        echo "  run     - Run the container"
        echo "  logs    - Show container logs"
        echo "  stop    - Stop the container"
        echo "  start   - Start the container"
        echo "  restart - Restart the container"
        echo "  deploy  - Build and run in one command"
        exit 1
        ;;
esac

exit 0