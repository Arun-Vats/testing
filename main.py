import asyncio
import time
from telethon import TelegramClient, events
from config import Config, logger
from database import Database
from search import SearchEngine
from handlers import MessageHandler
from datetime import datetime, timedelta

class TelegramSearchBot:
   def __init__(self):
       self.config = Config()
       self.db = Database(self.config.MONGO_URI)
       self.search_engine = SearchEngine()
       self.setup_client()
       
   def setup_client(self):
       self.bot = TelegramClient('bot_session', 
                               self.config.API_ID,
                               self.config.API_HASH)
       self.handler = MessageHandler(self.bot, self.db, self.search_engine)

   async def start_bot(self):
       try:
           self.bot.add_event_handler(self.handler.handle_message, 
                                    events.NewMessage)
           self.bot.add_event_handler(self.handler.handle_callback, 
                                    events.CallbackQuery)
           
           await self.bot.start(bot_token=self.config.BOT_TOKEN)
           logger.info("Bot started successfully")
           await self.bot.run_until_disconnected()
           
       except Exception as e:
           logger.error(f"Bot startup error: {e}")
           raise

   async def cleanup(self):
       try:
           self.db.close()
           await self.bot.disconnect()
           logger.info("Cleanup completed")
       except Exception as e:
           logger.error(f"Cleanup error: {e}")

   async def start(self):
       restart_delay = 10
       max_restart_delay = 300
       current_delay = restart_delay

       while True:
           try:
               await self.start_bot()
           except Exception as e:
               logger.error(f"Bot crashed: {e}")
               
               await self.cleanup()
               await asyncio.sleep(current_delay)
               
               # Exponential backoff
               current_delay = min(current_delay * 2, max_restart_delay)
               
               # Reset client
               self.setup_client()
           else:
               current_delay = restart_delay

def main():
   while True:
       try:
           bot = TelegramSearchBot()
           asyncio.run(bot.start())
       except KeyboardInterrupt:
           logger.info("Bot stopped by user")
           break
       except Exception as e:
           logger.critical(f"Fatal error: {e}")
           time.sleep(30)

if __name__ == "__main__":
   main()