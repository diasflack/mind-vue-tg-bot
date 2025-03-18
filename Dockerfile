# Альтернативная версия с Alpine Linux (меньше зависимостей)
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Установка переменных окружения для оптимизации Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONHASHSEED=random

# Install required system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    make \
    g++ \
    jpeg-dev \
    zlib-dev \
    libjpeg \
    freetype-dev \
    freetype

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psutil

# Create user data directory
RUN mkdir -p user_data visualization_cache && chmod 777 user_data visualization_cache

# Copy project files
COPY . .

# Use a volume for persistent data storage
VOLUME ["/app/user_data", "/app/visualization_cache"]

# Run the bot with optimized settings
CMD ["python", "main.py"]