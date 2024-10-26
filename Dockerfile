# Use Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy bot code to the container
COPY bot.py /app

# Install required packages
RUN pip install --no-cache-dir telethon==1.24.0  # Specific version for stability

# Set environment variables (configured later in Koyeb)
ENV API_ID=YOUR_API_ID
ENV API_HASH=YOUR_API_HASH
ENV BOT_TOKEN=YOUR_BOT_TOKEN

# Run the bot
CMD ["python", "bot.py"]
