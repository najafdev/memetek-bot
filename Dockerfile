FROM python:3.12-slim AS base

# System dependencies & security
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user for security
RUN groupadd -r memetek && useradd -r -g memetek -s /bin/false memetek

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY alembic.ini /app/
COPY memetek /app/memetek

# Set permissions
RUN chown -R memetek:memetek /app

USER memetek

EXPOSE 8080

# Healthcheck for FastAPI Dashboard and internal monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command: runs both Telegram bot and FastAPI dashboard concurrently
CMD ["python", "-m", "memetek.main", "all"]
