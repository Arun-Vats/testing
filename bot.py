from telethon import TelegramClient, events
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize Telegram Client with bot token
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Respond to /start command with a welcome message."""
    try:
        await event.reply("Welcome to Telegram!")
        logger.info("Responded to /start command.")
    except Exception as e:
        logger.error(f"Failed to respond to /start: {e}")

logger.info("Bot is running...")

# Run the bot
try:
    bot.run_until_disconnected()
except Exception as e:
    logger.critical(f"Bot has stopped due to an error: {e}")
