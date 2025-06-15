# handlers/admin.py
from telethon import events, Button
from database import delete_videos
from utils import generate_deep_link, check_privacy_policy, logger
from config import *
import base64
def register_admin_handlers(client, database_channel, admin_id, mongo_uri, videos_collection, users_collection):
    @client.on(events.NewMessage(pattern=r'/delete (.+)'))
    async def delete_handler(event):
        async def proceed(event):
            sender = await event.get_sender()
            if sender.id != admin_id:
                logger.info(f"Non-admin {sender.id} tried /delete")
                return
            ids_str = event.pattern_match.group(1).strip()
            if '-' in ids_str:
                start, end = map(int, ids_str.split('-'))
                ids = list(range(start, end + 1))
            elif ',' in ids_str:
                ids = [int(i.strip()) for i in ids_str.split(',')]
            else:
                ids = [int(ids_str)]
            delete_videos(videos_collection, ids)
            await client.delete_messages(database_channel, ids)
            await event.reply(DELETE_CONFIRMATION.format(count=len(ids)), parse_mode='html')

        if event.sender_id == admin_id:
            logger.info(f"Admin {admin_id} executing /delete")
            await proceed(event)
        else:
            accepted, msg = await check_privacy_policy(client, event, users_collection)
            if accepted:
                await proceed(event)

    @client.on(events.NewMessage(pattern=r'/link(?:\s+(.+))?'))
    async def link_handler(event):
        sender = await event.get_sender()
        logger.info(f"Sender ID: {sender.id}, Admin ID: {admin_id}")
        if sender.id != admin_id:
            logger.info(f"Non-admin {sender.id} tried /link")
            return
        movie_name = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else None
        if not movie_name:
            await event.reply(LINK_NO_MOVIE_MESSAGE, parse_mode='html')
            return
        encoded_movie = base64.urlsafe_b64encode(movie_name.encode('utf-8')).decode('utf-8').rstrip('=')
        deep_link = generate_deep_link(BOT_USERNAME, movie_name)
        buttons = [
            [Button.inline(BUTTON_YES, data=f"post_yes:{encoded_movie}"), Button.inline(BUTTON_NO, data="post_no")]
        ]
        await event.reply(
            LINK_PROMPT_MESSAGE.format(deep_link=deep_link),
            buttons=buttons,
            parse_mode='html'
        )