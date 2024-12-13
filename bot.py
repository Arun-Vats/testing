import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from aiohttp import web
import asyncio
import os
import platform
from datetime import datetime
import sys
from typing import Optional

import psutil

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Bot initialization with retry mechanism
class RetryBot(Bot):
    async def make_request(self, *args, **kwargs):
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                return await super().make_request(*args, **kwargs)
            except TelegramAPIError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"API request failed, attempt {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))

# Bot and dispatcher initialization
from config import BOT_TOKEN
bot = RetryBot(token=BOT_TOKEN)
dp = Dispatcher()

class HealthMonitor:
    def __init__(self):
        self.bot_start_time = datetime.now()
        self.last_message_time: Optional[datetime] = None
        self.is_polling = False
        self.web_app_running = False
        self.last_error = None

    def update_message_time(self):
        self.last_message_time = datetime.now()

    def get_formatted_uptime(self):
        uptime = datetime.now() - self.bot_start_time
        days, seconds = uptime.days, uptime.seconds
        
        components = []
        if days > 0:
            components.append(f"{days}d")
        
        hours, remainder = divmod(seconds, 3600)
        if hours > 0:
            components.append(f"{hours}h")
        
        minutes, secs = divmod(remainder, 60)
        if minutes > 0:
            components.append(f"{minutes}m")
        
        if secs > 0 or not components:
            components.append(f"{secs}s")
        
        return " ".join(components)

    def get_system_stats(self):
        # Memory calculation
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 ** 2)  # Total memory in MB
        memory_used = memory.used / (1024 ** 2)    # Used memory in MB
        
        # CPU usage calculation
        cpu_total = 100  # Total CPU percentage
        cpu_used = psutil.cpu_percent(interval=1)  # Current CPU usage
        
        return {
            "memory_used": memory_used,
            "memory_total": memory_total,
            "cpu_used": cpu_used,
            "cpu_total": cpu_total
        }

    def get_status_summary(self):
        stats = self.get_system_stats()
        return {
            "status": "healthy" if self.is_polling and self.web_app_running else "degraded",
            "uptime": self.get_formatted_uptime(),
            "polling": self.is_polling,
            "web_app": self.web_app_running,
            "system_stats": stats
        }

health_monitor = HealthMonitor()


# Centralized keyboard templates
def get_keyboard(current_screen='main'):
    keyboards = {
        'main': [
            [
                InlineKeyboardButton(text="🆘 Help", callback_data='help'),
                InlineKeyboardButton(text="ℹ️ About Us", callback_data='about')
            ],
            [
                InlineKeyboardButton(text="🔒 Privacy Policy", callback_data='privacy'),
                InlineKeyboardButton(text="🐞 Report Bug", callback_data='report_bug')
            ],
            [
                InlineKeyboardButton(text="❌ Close", callback_data='close')
            ]
        ],
        'help': [
            [
                InlineKeyboardButton(text="🏠 Home", callback_data='home'),
                InlineKeyboardButton(text="ℹ️ About Us", callback_data='about')
            ],
            [
                InlineKeyboardButton(text="🔒 Privacy Policy", callback_data='privacy'),
                InlineKeyboardButton(text="🐞 Report Bug", callback_data='report_bug')
            ],
            [
                InlineKeyboardButton(text="❌ Close", callback_data='close')
            ]
        ],
        'about': [
            [
                InlineKeyboardButton(text="🏠 Home", callback_data='home'),
                InlineKeyboardButton(text="🆘 Help", callback_data='help')
            ],
            [
                InlineKeyboardButton(text="🔒 Privacy Policy", callback_data='privacy'),
                InlineKeyboardButton(text="🐞 Report Bug", callback_data='report_bug')
            ],
            [
                InlineKeyboardButton(text="❌ Close", callback_data='close')
            ]
        ],
        'privacy': [
            [
                InlineKeyboardButton(text="🏠 Home", callback_data='home'),
                InlineKeyboardButton(text="🆘 Help", callback_data='help')
            ],
            [
                InlineKeyboardButton(text="ℹ️ About Us", callback_data='about'),
                InlineKeyboardButton(text="🐞 Report Bug", callback_data='report_bug')
            ],
            [
                InlineKeyboardButton(text="❌ Close", callback_data='close')
            ]
        ],
        'report_bug': [
            [
                InlineKeyboardButton(text="🏠 Home", callback_data='home'),
                InlineKeyboardButton(text="🆘 Help", callback_data='help')
            ],
            [
                InlineKeyboardButton(text="ℹ️ About Us", callback_data='about'),
                InlineKeyboardButton(text="🔒 Privacy Policy", callback_data='privacy')
            ],
            [
                InlineKeyboardButton(text="❌ Close", callback_data='close')
            ]
        ]
    }
    return InlineKeyboardMarkup(inline_keyboard=keyboards[current_screen])

# Content dictionary
CONTENT = {
    'main': "Welcome to CinemaSearch! 🎬🍿 Discover movies and series with just a few clicks. What cinematic adventure are you craving today? 🎥✨",
    'help': "🆘 Need a movie magic guide? Here's how to use CinemaSearch:\n\n• 🔍 Type a movie/series name to start searching\n• 🏠 Use /start to return to the main menu\n• 🧭 Explore more with the buttons below\n\nLet's find your perfect film! 🎬🍿",
    'about': "CinemaSearch: Your Ultimate Movie Companion! 🎥🌟\n\n🚀 Our Mission: Bringing the world of cinema to your fingertips!\n\n• 🍿 Quick movie discoveries\n• 🌈 Endless entertainment possibilities\n• ❤️ Powered by film passion\n\nWe're here to make your movie night awesome! 🎬💖",
    'privacy': "🔒 Privacy Policy:\n\n• 🛡️ Your data is our top priority\n• 🤐 No personal info stored or shared\n• 🔐 Confidential search queries\n• 🍪 Essential cookies only\n\nYour digital safety, our promise! 💯🛡️",
    'report_bug': "🐞 Found a bug? We appreciate your help!\n\n• Please describe the issue in detail\n• Include steps to reproduce\n• Share any error messages\n\nYou can report bugs to: support@cinemasearch.com"
}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        await message.delete()
        await message.answer(
            text=CONTENT['main'], 
            reply_markup=get_keyboard('main')
        )
        health_monitor.update_message_time()
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("An error occurred. Please try again later.")

@dp.message(Command("uptime"))
async def cmd_uptime(message: types.Message):
    try:
        health_monitor.update_message_time()
        status = health_monitor.get_status_summary()
        stats = status['system_stats']
        
        status_message = (
            f"🤖 Bot Status Report:\n\n"
            f"⏱ Uptime: {status['uptime']}\n"
            f"🔄 Status: {'✅ Operational' if status['status'] == 'healthy' else '⚠️ Degraded'}\n"
            f"📡 Polling: {'✅ Active' if status['polling'] else '❌ Inactive'}\n"
            f"🌐 Web Server: {'✅ Running' if status['web_app'] else '❌ Down'}\n"
            f"💻 Platform: {platform.system()}\n"
            f"🖥 CPU Usage: {stats['cpu_used']:.1f}/{stats['cpu_total']} %\n"
            f"💽 Memory Usage: {stats['memory_used']:.1f}/{stats['memory_total']:.1f} MB\n"
        )
        
        await message.answer(status_message)
    except Exception as e:
        logger.error(f"Error in uptime command: {e}")
        await message.answer("An error occurred while fetching the status.")


# Enhanced callback query handler
@dp.callback_query(F.data.in_(['home', 'help', 'about', 'privacy', 'close', 'report_bug']))
async def handle_callback(callback: types.CallbackQuery):
    try:
        if callback.data == 'close':
            await callback.message.delete()
            await callback.answer("Message closed")
            return

        screen_map = {
            'home': 'main',
            'help': 'help',
            'about': 'about',
            'privacy': 'privacy',
            'report_bug': 'report_bug'
        }
        
        current_screen = screen_map.get(callback.data, 'main')
        
        await callback.message.edit_text(
            text=CONTENT[current_screen], 
            reply_markup=get_keyboard(current_screen)
        )
        await callback.answer()
        health_monitor.update_message_time()
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await callback.answer("An error occurred. Please try again.")

# Enhanced web application
async def start_web_app():
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    # Cleanup handler
    async def cleanup(app):
        logger.info("Shutting down bot...")
        try:
            await bot.session.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Cleanup completed")
    
    app.on_cleanup.append(cleanup)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    health_monitor.web_app_running = True
    logger.info(f"Web server started on port {port}")
    return app, runner

# Enhanced health check
async def health_check(request):
    return web.json_response(health_monitor.get_status())

# Main function with enhanced error handling
async def main():
    runner = None
    try:
        # Start web server
        app, runner = await start_web_app()
        
        # Start bot polling with reconnection logic
        while True:
            try:
                health_monitor.is_polling = True
                logger.info("Starting bot polling...")
                await dp.start_polling(bot)
            except Exception as e:
                health_monitor.is_polling = False
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)  # Wait before retry
                
    except Exception as e:
        logger.critical(f"Critical error: {e}")
    finally:
        if runner:
            logger.info("Cleaning up...")
            await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)
