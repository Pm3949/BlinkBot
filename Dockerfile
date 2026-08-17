FROM python:3.11-slim

# Install system dependencies required for psycopg2, compiling libraries, and OCR features
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    make \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements file first to optimize docker caching layer
COPY server-python/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase to app directory
COPY server-python/ /app/

EXPOSE 8000 8001
