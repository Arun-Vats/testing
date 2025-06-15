import os
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv
from database import get_videos_collection, get_users_collection
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.common import register_common_handlers
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI
import logging
from aiohttp import web

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate required environment variables
required_vars = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "DATABASE_CHANNEL_ID": DATABASE_CHANNEL_ID,
    "ADMIN_ID": ADMIN_ID,
    "MONGO_URI": MONGO_URI
}
for var_name, var_value in required_vars.items():
    if not var_value:
        logger.error(f"Required environment variable '{var_name}' is not set. Exiting.")
        raise ValueError(f"Required environment variable '{var_name}' is not set.")

# Initialize Telethon client
client = TelegramClient("session_name", API_ID, API_HASH)

# Get MongoDB collections
videos_collection = get_videos_collection(MONGO_URI)
users_collection = get_users_collection(MONGO_URI)

# Register all handlers
register_common_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, videos_collection, users_collection)
register_admin_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI, videos_collection, users_collection)
register_user_handlers(client, videos_collection, users_collection)

# Optional: Add /ping command to check bot is alive
@client.on(events.NewMessage(pattern="/ping"))
async def ping_handler(event):
    await event.reply("I'm alive! ✅")

# Health check endpoint for Koyeb
async def health_check(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get("/", health_check)])

# Start Telegram bot
async def start_bot():
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Bot started successfully.")
        await client.run_until_disconnected()
    except Exception as e:
        logger.exception("❌ Bot crashed unexpectedly!")

# Start web server (used for Koyeb health check)
async def start_web_server():
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        logger.info("🌐 Health check web server running on port 8000.")
    except Exception as e:
        logger.exception("❌ Web server failed to start!")

# Main entry point
async def main():
    await asyncio.gather(start_bot(), start_web_server())

if __name__ == "__main__":
    logger.info("🚀 Starting bot and web server...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.exception("❌ Main loop crashed!")
