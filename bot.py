from telethon import TelegramClient, events
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Telegram Client
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

# HTTP Server for health check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_health_check_server():
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    logger.info("Starting HTTP server for health check on port 8000...")
    server.serve_forever()

# Run HTTP server in a separate thread
threading.Thread(target=run_health_check_server, daemon=True).start()

# Run the bot
try:
    bot.run_until_disconnected()
except Exception as e:
    logger.critical(f"Bot has stopped due to an error: {e}")
