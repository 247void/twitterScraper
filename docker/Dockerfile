FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libmagic1 \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install specific httpx version that works with tweety
RUN pip install httpx tweety-ns

# Copy requirements first for better caching
COPY pyproject.toml .
RUN pip install -e .

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run python with unbuffered output
CMD ["python", "-u", "main.py"] 