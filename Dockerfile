# Use Python slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \  # Added for healthcheck
    && rm -rf /var/lib/apt/lists/*

# Create and switch to non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Copy requirements first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --retries 3 -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create config directory if using python-dotenv
RUN mkdir -p /app/config && \
    chown -R appuser:appuser /app/config

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck using the health endpoint from bot.py
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["python", "bot.py"]
