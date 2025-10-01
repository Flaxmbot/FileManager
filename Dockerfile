# Multi-stage Dockerfile for FileManager Telegram Bot
# Stage 1: Builder
FROM python:3.12-slim as builder

# Set build arguments
ARG NODE_ENV=production

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi8 \
    libssl3 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# Create non-root user for security
RUN groupadd -r appuser -g 1000 && \
    useradd -r -g appuser -u 1000 -d /app -s /bin/bash appuser

# Set work directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/keys /app/logs /app/data && \
    chown -R appuser:appuser /app

# Set proper permissions for security
RUN chmod 755 /app && \
    chmod 644 requirements.txt && \
    find /app -type d -exec chmod 755 {} \; && \
    find /app -type f -exec chmod 644 {} \; && \
    chmod 755 /app/src/main.py

# Switch to non-root user
USER appuser

# Create health check script
RUN echo '#!/bin/bash\n\
import sys\n\
import requests\n\
try:\n\
    response = requests.get("http://localhost:10000/health", timeout=5)\n\
    sys.exit(0 if response.status_code == 200 else 1)\n\
except:\n\
    sys.exit(1)' > /app/healthcheck.py && \
    chmod +x /app/healthcheck.py

# Expose port
EXPOSE 10000

# Health check with proper configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Resource limits are better set through Docker run command or compose file
# Start command with proper configuration
CMD ["python", "-m", "src.main"]