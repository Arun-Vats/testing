import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Bot initialization
from config import BOT_TOKEN
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

# Start command handler
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Delete the user's /start message
    await message.delete()
    
    # Send the welcome message
    sent_message = await message.answer(
        text=CONTENT['main'], 
        reply_markup=get_keyboard('main')
    )

# Callback query handler
@dp.callback_query(F.data.in_(['home', 'help', 'about', 'privacy', 'close', 'report_bug']))
async def handle_callback(callback: types.CallbackQuery):
    # Handle close button
    if callback.data == 'close':
        await callback.message.delete()
        await callback.answer("Message closed")
        return
    
    # Handle report bug
    if callback.data == 'report_bug':
        await callback.message.edit_text(
            text=CONTENT['report_bug'], 
            reply_markup=get_keyboard('report_bug')
        )
        await callback.answer()
        return
    
    # Existing screen mapping logic
    screen_map = {
        'home': 'main',
        'help': 'help',
        'about': 'about',
        'privacy': 'privacy'
    }
    
    current_screen = screen_map.get(callback.data, 'main')
    
    await callback.message.edit_text(
        text=CONTENT[current_screen], 
        reply_markup=get_keyboard(current_screen)
    )
    await callback.answer()

async def start_web_app():
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# Modify your main() function
async def main():
    try:
        # Start web server
        await start_web_app()
        
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
