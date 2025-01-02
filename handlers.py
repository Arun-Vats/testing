from telethon import Button
from config import logger, Config

class MessageHandler:
   def __init__(self, bot, db, search_engine):
       self.bot = bot
       self.db = db
       self.search_engine = search_engine
       self.config = Config()

   async def handle_message(self, event):
       try:
           message = event.text.strip()
           if not message or len(message) < 2:
               await event.reply("Please provide a search term (minimum 2 characters)")
               return
           await self.display_results(event, message)
       except Exception as e:
           logger.error(f"Error in handle_message: {e}")
           await event.reply("An error occurred. Please try again.")

   async def handle_callback(self, event):
       try:
           data = event.data.decode()
           
           if data.startswith("prev_"):
               _, current_page, query = data.split("_", 2)
               await self.display_results(event, query, int(current_page))
           
           elif data.startswith("next_"):
               _, current_page, query = data.split("_", 2)
               await self.display_results(event, query, int(current_page))
           
           elif data.startswith("item_"):
               _, file_id, query = data.split("_", 2)
               await self.display_result_details(event, file_id)
           
           elif data == "close":
               try:
                   await event.delete()
               except Exception as e:
                   logger.error(f"Error closing message: {e}")
                   await event.answer("Failed to close. Please try again.", alert=True)
           
           elif data == "page_info":
               await event.answer("Current page information")

       except Exception as e:
           logger.error(f"Error in handle_callback: {e}")
           await event.answer("Error processing button. Please try again.")

   async def display_result_details(self, event, file_id):
       try:
           channel_message = await self.bot.get_messages(self.config.CHANNEL_ID, ids=int(file_id))
       
           if not channel_message:
               await event.answer("File not found in channel!")
               return
       
           file = channel_message.media
           caption = channel_message.message or "No caption"

           await self.bot.send_file(
               event.chat_id,
               file=file,
               caption=caption
           )
       
           await event.answer("File sent successfully!")
       
       except Exception as e:
           logger.error(f"Error displaying result: {e}")
           await event.answer("Error accessing file. Please try again.")

   async def display_results(self, event, search_query, page=0):
       try:
           search_pattern = self.search_engine.prepare_query(search_query)
           query = {"caption": {"$regex": search_pattern, "$options": "i"}}
       
           total_results = await self.bot.loop.run_in_executor(
               None, self.db.count_documents, query
           )
       
           if total_results == 0:
               await event.reply("No results found.")
               return

           total_pages = -(-total_results // self.config.RESULTS_PER_PAGE)  # Math.ceil equivalent
           page = max(0, min(page, total_pages - 1))
       
           results = await self.bot.loop.run_in_executor(
               None,
               lambda: self.db.find_documents(
                   query,
                   {"_id": 1, "caption": 1, "file_size": 1},
                   page * self.config.RESULTS_PER_PAGE,
                   self.config.RESULTS_PER_PAGE
               )
           )

           buttons = [
               [Button.inline(
                   f"[{result['file_size']}] {result['caption'][:40]}...", 
                   f"item_{result['_id']}_{search_query}"
               )] for result in results
           ]

           if total_pages > 1:
               nav = []
               if page > 0:
                   nav.append(Button.inline("⬅️ Previous", f"prev_{page - 1}_{search_query}"))
           
               nav.append(Button.inline(f"Page {page + 1}/{total_pages}", f"page_info"))
           
               if page < total_pages - 1:
                   nav.append(Button.inline("Next ➡️", f"next_{page + 1}_{search_query}"))
           
               buttons.append(nav)

           buttons.append([Button.inline("❌ Close", "close")])
           message = f"Search Results for '{search_query}'"

           if hasattr(event, 'message'):
               await event.reply(message, buttons=buttons)
           else:
               await event.edit(message, buttons=buttons)

       except Exception as e:
           logger.error(f"Error in display_results: {e}")
           error_msg = "An error occurred. Please try a new search."
           if hasattr(event, 'message'):
               await event.reply(error_msg)
           else:
               await event.answer(error_msg)