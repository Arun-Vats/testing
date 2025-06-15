from telethon import events, Button
from telethon.errors import MessageNotModifiedError
from .common import search_handler
from utils import decode_deep_link, check_privacy_policy, logger
from config import *
from database import accept_privacy_policy
from datetime import datetime

def register_user_handlers(client, videos_collection, users_collection):
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        if event.is_private:
            logger.info(f"Handling /start for user {event.sender_id}")
            
            async def proceed(event):
                args = event.message.text.split(maxsplit=1)
                if len(args) > 1:
                    encoded_query = args[1]
                    try:
                        query = decode_deep_link(encoded_query)
                        await search_handler(event, query=query, videos_collection=videos_collection)
                    except Exception:
                        await event.reply(START_MESSAGE, parse_mode='markdown')
                else:
                    await event.reply(START_MESSAGE, parse_mode='markdown')
            
            accepted, msg = await check_privacy_policy(client, event, users_collection)
            if not accepted:
                @client.on(events.CallbackQuery(data=f"accept_privacy:{event.sender_id}"))
                async def accept_handler(callback_event):
                    if callback_event.sender_id == event.sender_id:
                        logger.info(f"User {event.sender_id} accepted privacy policy")
                        accept_privacy_policy(users_collection, event.sender_id)
                        try:
                            await callback_event.edit(
                                PRIVACY_ACCEPTED_MESSAGE,
                                buttons=None,
                                parse_mode='html'
                            )
                        except MessageNotModifiedError:
                            logger.info(f"Message not modified for user {event.sender_id}, proceeding anyway")
                        await proceed(event)
                        client.remove_event_handler(accept_handler)
            else:
                await proceed(event)

    @client.on(events.NewMessage(pattern=r'^/plan$'))
    async def handle_plan(event):
        logger.info(f"Received /plan command from user {event.sender_id}")
        user_id = event.sender_id
        
        user_data = users_collection.find_one({"_id": user_id})
        logger.info(f"Raw user data for {user_id}: {user_data}")
        
        current_date = datetime.now()
        close_button = [[Button.inline(BUTTON_CLOSE, data="close")]]
        
        if not user_data or "is_paid" not in user_data:
            logger.info(f"User {user_id} has no subscription data")
            await event.reply(
                PLAN_NO_SUBSCRIPTION,
                buttons=[
                    [Button.inline("🔋 " + BUTTON_RECHARGE, data="recharge")],
                    close_button[0]
                ],
                parse_mode='html'
            )
        else:
            is_paid = user_data.get("is_paid", False)
            expiry_date = user_data.get("expiry_date")
            plan_description = user_data.get("plan_description", "Unknown Plan")
            paid_duration = user_data.get("paid_duration", 0)
            
            if is_paid and expiry_date and current_date <= expiry_date:
                remaining_days = (expiry_date - current_date).days
                expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"User {user_id} has active subscription, expires {expiry_str}")
                await event.reply(
                    PLAN_ACTIVE_SUBSCRIPTION.format(
                        plan_description=plan_description,
                        paid_duration=paid_duration,
                        expiry_date=expiry_str,
                        remaining_days=f"{remaining_days} days"
                    ),
                    buttons=close_button,
                    parse_mode='html'
                )
            else:
                expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S") if expiry_date else "Not set"
                logger.info(f"User {user_id} subscription expired or inactive, last expiry: {expiry_str}")
                await event.reply(
                    PLAN_EXPIRED_SUBSCRIPTION.format(
                        plan_description=plan_description,
                        paid_duration=paid_duration,
                        expiry_date=expiry_str
                    ),
                    buttons=[
                        [Button.inline("🔋 " + BUTTON_RECHARGE, data="recharge")],
                        close_button[0]
                    ],
                    parse_mode='html'
                )
        
        logger.info(f"Sent /plan response to user {user_id}")

    @client.on(events.NewMessage(incoming=True))
    async def message_handler(event):
        if event.is_private and not event.message.text.startswith('/start') and not event.photo:
            logger.info(f"Handling message '{event.message.text}' for user {event.sender_id}")
            
            async def proceed(event):
                if event.sender_id == ADMIN_ID and event.message.text.startswith(('/link', '/delete')):
                    logger.info(f"Skipping admin command '{event.message.text}' for user {event.sender_id}")
                    return
                if event.message.text.startswith('/') and event.message.text != '/plan':
                    await event.reply(UNKNOWN_COMMAND_MESSAGE, parse_mode='html')
                else:
                    await search_handler(event, videos_collection=videos_collection)
            
            accepted, msg = await check_privacy_policy(client, event, users_collection)
            if not accepted:
                @client.on(events.CallbackQuery(data=f"accept_privacy:{event.sender_id}"))
                async def accept_handler(callback_event):
                    if callback_event.sender_id == event.sender_id:
                        logger.info(f"User {event.sender_id} accepted privacy policy")
                        accept_privacy_policy(users_collection, event.sender_id)
                        try:
                            await callback_event.edit(
                                PRIVACY_ACCEPTED_MESSAGE,
                                buttons=None,
                                parse_mode='html'
                            )
                        except MessageNotModifiedError:
                            logger.info(f"Message not modified for user {event.sender_id}, proceeding anyway")
                        await proceed(event)
                        client.remove_event_handler(accept_handler)
            else:
                await proceed(event)