# Use Alpine Linux as base image
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Install required system dependencies for building Python packages
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
    pip install --no-cache-dir -r requirements.txt

# Create user data directory
RUN mkdir -p user_data && chmod 777 user_data

# Copy project files
COPY . .

# Use a volume for persistent data storage
VOLUME ["/app/user_data"]

# Run the bot
CMD ["python", "main.py"]