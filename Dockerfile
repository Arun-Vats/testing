# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to non-root user
RUN useradd -m botuser

# Ensure the app directory is writable by botuser
RUN chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Copy requirements file first to leverage Docker cache
COPY --chown=botuser:botuser requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=botuser:botuser . .

# Expose port (if needed)
EXPOSE 8000

# Command to run the application
CMD ["python", "bot.py"]
