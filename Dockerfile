FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including libpq-dev for asyncpg
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create logs directory
RUN mkdir -p /app/logs

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install asyncpg FIRST (before any other packages)
RUN pip install --no-cache-dir asyncpg==0.31.0 --force-reinstall --no-deps

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Render uses 8080, also support 10000)
EXPOSE 8080
EXPOSE 10000

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - can be overridden
# For Render: uses port 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]