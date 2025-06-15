from telethon import events, Button, errors
import re
import asyncio
from database import save_video, update_user_subscription
from utils import convert_file_size, normalize_query, fetch_tmdb_details, check_privacy_policy, logger
from config import *
from handlers.subscription import check_and_handle_subscription
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

async def search_handler(event, query=None, videos_collection=None):
    if event.is_private and (query or not event.message.text.startswith('/')):
        query = query or event.message.text.strip()
        clean_query = normalize_query(query)
        regex_pattern = ".*".join(re.escape(word) for word in clean_query.split())
        results = list(videos_collection.find({"caption": {"$regex": regex_pattern, "$options": "i"}}))
        if not results:
            await event.reply(NO_RESULTS_MESSAGE.format(query=query), parse_mode='html')
            return
        tmdb_details = fetch_tmdb_details(query)
        page = 0
        per_page = 5
        total_pages = (len(results) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        buttons = []
        for doc in results[start:end]:
            caption = doc["caption"][:50] + "..." if len(doc["caption"]) > 50 else doc["caption"]
            button_text = f"[{doc['file_size']}] {caption}"
            buttons.append([Button.inline(button_text, data=f"select:{doc['_id']}")])
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(Button.inline(BUTTON_PREV, data=f"page:{query}:{page-1}:none:none"))
            nav_buttons.append(Button.inline(BUTTON_PAGE_INFO.format(page=page+1, total=total_pages), data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(Button.inline(BUTTON_NEXT, data=f"page:{query}:{page+1}:none:none"))
            buttons.append(nav_buttons)
        quality_counts = {
            "2160p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p"}),
            "1080p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p"}),
            "720p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p"}),
            "480p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p"})
        }
        quality_buttons = []
        for quality, count in quality_counts.items():
            if count > 0:
                quality_buttons.append(Button.inline(f"{quality}", data=f"quality:{query}:{quality}:none:none"))
        if quality_buttons:
            buttons.append(quality_buttons)
        movie_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "movie"
        })
        series_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "series"
        })
        filter_buttons = []
        if movie_count > 0:
            filter_buttons.append(Button.inline(BUTTON_MOVIES, data=f"filter:{query}:movie:none:none"))
        if series_count > 0:
            filter_buttons.append(Button.inline(BUTTON_SERIES, data=f"filter:{query}:series:none:none"))
        buttons.append(filter_buttons)
        buttons.append([Button.inline(BUTTON_CLOSE, data="close")])
        if tmdb_details:
            # Dynamically construct the message based on available details
            message_lines = [f"{EMOJI_TYPE} <b>{tmdb_details['type']}</b> :- <a href='{tmdb_details['poster_url']}'>{tmdb_details['name']}</a>"]
            if tmdb_details.get('release_line'):
                message_lines.append(f"{EMOJI_RELEASE} {tmdb_details['release_line']}")
            if tmdb_details.get('rating_line'):
                message_lines.append(f"{EMOJI_RATING} {tmdb_details['rating_line']}")
            if tmdb_details.get('duration_line'):
                message_lines.append(f"{EMOJI_DURATION} {tmdb_details['duration_line']}")
            if tmdb_details.get('season_line'):
                message_lines.append(f"{EMOJI_SEASON} {tmdb_details['season_line']}")
            if tmdb_details.get('audio_line'):
                message_lines.append(f"{EMOJI_AUDIO} {tmdb_details['audio_line']}")
            if tmdb_details.get('genre_line'):
                message_lines.append(f"{EMOJI_GENRE} {tmdb_details['genre_line']}")
            if tmdb_details.get('trailer_line'):
                message_lines.append(f"{EMOJI_TRAILER} {tmdb_details['trailer_line']}")
            if tmdb_details.get('platforms_line'):
                message_lines.append(f"{EMOJI_PLATFORMS} {tmdb_details['platforms_line']}")
            message = "\n".join(message_lines)
            await event.reply(
                message,
                buttons=buttons,
                parse_mode='html'
            )
        else:
            await event.reply(
                FALLBACK_SEARCH_RESULT_MESSAGE.format(query=query),
                buttons=buttons,
                parse_mode='html'
            )

def register_common_handlers(client, database_channel, admin_id, videos_collection, users_collection):
    @client.on(events.NewMessage(chats=database_channel))
    async def handle_video(event):
        if event.video:
            message_id = event.message.id
            caption = event.message.message or ""
            file_size = event.message.file.size
            file_size_str = convert_file_size(file_size)
            series_patterns = [r'E\d+', r'S\d+', r'S\d+E\d+']
            category = "series" if any(re.search(pattern, caption, re.IGNORECASE) for pattern in series_patterns) else "movie"
            quality_patterns = [r'2160[Pp]', r'1080[Pp]', r'720[Pp]', r'480[Pp]']
            quality = next((re.search(pattern, caption, re.IGNORECASE).group().lower() for pattern in quality_patterns if re.search(pattern, caption, re.IGNORECASE)), "unknown")
            video_data = {
                "_id": message_id,
                "caption": caption,
                "file_size": file_size_str,
                "category": category,
                "quality": quality
            }
            save_video(videos_collection, video_data)

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode()
        user_id = event.sender_id
        logger.info(f"Handling callback '{data}' for user {user_id}")
        if data.startswith("accept_privacy:"):
            if data == f"accept_privacy:{user_id}":
                logger.info(f"User {user_id} accepting privacy policy")
                from database import accept_privacy_policy
                accept_privacy_policy(users_collection, user_id)
                await event.edit(PRIVACY_ACCEPTED_MESSAGE, parse_mode='html')
            return

        accepted, msg = await check_privacy_policy(client, event, users_collection)
        if accepted:
            await process_callback(client, event, data, database_channel, admin_id, videos_collection, users_collection)

async def process_callback(client, event, data, database_channel, admin_id, videos_collection, users_collection):
    logger.info(f"Processing callback '{data}' for user {event.sender_id}")
    if data.startswith("select:"):
        msg_id = int(data.split(":")[1])
        file_message = await client.get_messages(database_channel, ids=msg_id)
        await check_and_handle_subscription(client, event, event.sender_id, users_collection, file_message)
    elif data == "recharge":
        await event.edit(
            RECHARGE_PROMPT_MESSAGE,
            buttons=[
                [Button.inline("₹40 - 1 Month", data="plan:30:40")],
                [Button.inline("₹120 - 3 Months", data="plan:90:120")],
                [Button.inline("₹240 - 6 Months", data="plan:180:240")],
                [Button.inline("₹480 - 12 Months", data="plan:360:480")],
                [Button.inline(BUTTON_CLOSE, data="close")]
            ],
            parse_mode='html'
        )
    elif data.startswith("plan:"):
        days, amount = map(int, data.split(":")[1:])
        user_id = event.sender_id
        await event.delete()
        qr_message = await client.get_messages(database_channel, ids=QR_PHOTO_ID)
        payment_message_text = PAYMENT_REQUEST_MESSAGE.format(amount=amount, payment_id=PAYMENT_ID)
        if not qr_message or not qr_message.photo:
            logger.error(f"QR code message ID {QR_PHOTO_ID} not found or has no photo in database channel")
            payment_message = await client.send_message(
                user_id,
                payment_message_text,
                buttons=[[Button.inline(BUTTON_CANCEL, data=f"cancel_payment:{user_id}")]],
                parse_mode='html'
            )
        else:
            payment_message = await client.send_message(
                user_id,
                payment_message_text,
                file=qr_message.media,
                buttons=[[Button.inline(BUTTON_CANCEL, data=f"cancel_payment:{user_id}")]],
                parse_mode='html'
            )
        logger.info(f"Payment request with QR sent to user {user_id}, message ID {payment_message.id}")

        payment_done = asyncio.Event()

        async def screenshot_handler(inner_event):
            if inner_event.is_private and inner_event.sender_id == user_id:
                if inner_event.photo:
                    logger.info(f"Screenshot received from user {user_id}")
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    admin_message_text = PAYMENT_ADMIN_REQUEST_MESSAGE.format(
                        user_id=user_id, amount=amount, days=days, timestamp=timestamp
                    )
                    await client.send_message(
                        ADMIN_ID,
                        admin_message_text,
                        file=inner_event.message.media,
                        buttons=[
                            [Button.inline("✅ Confirm", data=f"confirm_payment:{user_id}:{days}:{amount}"),
                             Button.inline("❌ Reject", data=f"reject_payment:{user_id}")]
                        ],
                        parse_mode='html'
                    )
                    await inner_event.message.delete()
                    await payment_message.delete()
                    await client.send_message(user_id, PAYMENT_VERIFICATION_MESSAGE, parse_mode='html')
                    payment_done.set()
                else:
                    logger.info(f"Ignoring non-photo message from user {user_id}: {inner_event.message.text or 'media'}")
                    await inner_event.message.delete()
                raise events.StopPropagation

        async def cancel_payment_handler(cancel_event):
            if cancel_event.sender_id == user_id and cancel_event.data == f"cancel_payment:{user_id}".encode():
                logger.info(f"User {user_id} canceled payment process")
                await payment_message.delete()
                await client.send_message(user_id, PAYMENT_CANCELLED_MESSAGE, parse_mode='html')
                payment_done.set()
                raise events.StopPropagation

        client.add_event_handler(screenshot_handler, events.NewMessage(incoming=True))
        client.add_event_handler(cancel_payment_handler, events.CallbackQuery())

        try:
            await asyncio.wait_for(payment_done.wait(), timeout=300)
        except asyncio.TimeoutError:
            logger.info(f"Timeout reached, deleting message ID {payment_message.id} for user {user_id}")
            await payment_message.delete()
            await client.send_message(
                user_id,
                PAYMENT_TIMEOUT_MESSAGE,
                buttons=[Button.inline("♻️Send Again♻️", data=f"plan:{days}:{amount}")],
                parse_mode='html'
            )
            logger.info(f"Payment timeout for user {user_id}")

        client.remove_event_handler(screenshot_handler)
        client.remove_event_handler(cancel_payment_handler)

    elif data.startswith("confirm_payment:"):
        parts = data.split(":")
        user_id, days, amount = int(parts[1]), int(parts[2]), int(parts[3])
        if event.sender_id == admin_id:
            logger.info(f"Admin {admin_id} confirmed payment for user {user_id}: {amount}₹ for {days} days")
            expiry_date = datetime.now() + timedelta(days=days)
            update_user_subscription(
                users_collection,
                user_id,
                {
                    "paid_duration": days,
                    "is_paid": True,
                    "plan_description": f"{days}-Day Plan",
                    "expiry_date": expiry_date
                }
            )
            logger.info(f"Updated subscription for user {user_id}: {days} days, expiry: {expiry_date}")
            await client.send_message(user_id, PAYMENT_CONFIRMED_MESSAGE.format(amount=amount, days=days), parse_mode='html')
            logger.info(f"Deleting admin message with screenshot for user {user_id}")
            await event.delete()
            await client.send_message(
                ADMIN_ID,
                PAYMENT_ADMIN_CONFIRMED_MESSAGE.format(user_id=user_id, amount=amount, days=days),
                parse_mode='html'
            )
        else:
            await event.answer(PAYMENT_ADMIN_ONLY_MESSAGE)

    elif data.startswith("reject_payment:"):
        user_id = int(data.split(":")[1])
        if event.sender_id == admin_id:
            logger.info(f"Admin {admin_id} rejected payment for user {user_id}")
            await client.send_message(user_id, PAYMENT_REJECTED_MESSAGE, parse_mode='html')
            logger.info(f"Deleting admin message with screenshot for user {user_id}")
            await event.delete()
            await client.send_message(
                ADMIN_ID,
                PAYMENT_ADMIN_REJECTED_MESSAGE.format(user_id=user_id),
                parse_mode='html'
            )
        else:
            await event.answer(PAYMENT_ADMIN_ONLY_MESSAGE)

    elif data.startswith("page:"):
        query, page, category, quality = data.split(":")[1], int(data.split(":")[2]), data.split(":")[3], data.split(":")[4] if len(data.split(":")) > 4 else None
        tmdb_details = fetch_tmdb_details(query)
        clean_query = normalize_query(query)
        regex_pattern = ".*".join(re.escape(word) for word in clean_query.split())
        filter_query = {"caption": {"$regex": regex_pattern, "$options": "i"}}
        if category and category != "none":
            filter_query["category"] = category
        if quality and quality != "none":
            filter_query["quality"] = quality
        results = list(videos_collection.find(filter_query))
        per_page = 5
        total_pages = (len(results) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        buttons = []
        for doc in results[start:end]:
            caption = doc["caption"][:50] + "..." if len(doc["caption"]) > 50 else doc["caption"]
            button_text = f"[{doc['file_size']}] {caption}"
            buttons.append([Button.inline(button_text, data=f"select:{doc['_id']}")])
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(Button.inline(BUTTON_PREV, data=f"page:{query}:{page-1}:{category or 'none'}:{quality or 'none'}"))
            nav_buttons.append(Button.inline(BUTTON_PAGE_INFO.format(page=page+1, total=total_pages), data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(Button.inline(BUTTON_NEXT, data=f"page:{query}:{page+1}:{category or 'none'}:{quality or 'none'}"))
            buttons.append(nav_buttons)
        quality_counts = {
            "2160p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p", "category": category} if category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p"}),
            "1080p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p", "category": category} if category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p"}),
            "720p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p", "category": category} if category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p"}),
            "480p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p", "category": category} if category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p"})
        }
        quality_buttons = []
        for q, count in quality_counts.items():
            if count > 0:
                quality_buttons.append(Button.inline(f"{q}" + (BUTTON_TICK if quality == q else ""), data=f"quality:{query}:{q}:{category or 'none'}:{quality or 'none'}"))
        if quality_buttons:
            buttons.append(quality_buttons)
        movie_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "movie",
            "quality": quality if quality and quality != "none" else {"$exists": True}
        })
        series_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "series",
            "quality": quality if quality and quality != "none" else {"$exists": True}
        })
        filter_buttons = []
        if movie_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_MOVIES + (BUTTON_TICK if category == "movie" else ""),
                data=f"filter:{query}:movie:{quality or 'none'}:{category or 'none'}"
            ))
        if series_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_SERIES + (BUTTON_TICK if category == "series" else ""),
                data=f"filter:{query}:series:{quality or 'none'}:{category or 'none'}"
            ))
        buttons.append(filter_buttons)
        buttons.append([Button.inline(BUTTON_CLOSE, data="close")])
        try:
            if tmdb_details:
                message_lines = [f"{EMOJI_TYPE} <b>{tmdb_details['type']}</b> :- <a href='{tmdb_details['poster_url']}'>{tmdb_details['name']}</a>"]
                if tmdb_details.get('release_line'):
                    message_lines.append(f"{EMOJI_RELEASE} {tmdb_details['release_line']}")
                if tmdb_details.get('rating_line'):
                    message_lines.append(f"{EMOJI_RATING} {tmdb_details['rating_line']}")
                if tmdb_details.get('duration_line'):
                    message_lines.append(f"{EMOJI_DURATION} {tmdb_details['duration_line']}")
                if tmdb_details.get('season_line'):
                    message_lines.append(f"{EMOJI_SEASON} {tmdb_details['season_line']}")
                if tmdb_details.get('audio_line'):
                    message_lines.append(f"{EMOJI_AUDIO} {tmdb_details['audio_line']}")
                if tmdb_details.get('genre_line'):
                    message_lines.append(f"{EMOJI_GENRE} {tmdb_details['genre_line']}")
                if tmdb_details.get('trailer_line'):
                    message_lines.append(f"{EMOJI_TRAILER} {tmdb_details['trailer_line']}")
                if tmdb_details.get('platforms_line'):
                    message_lines.append(f"{EMOJI_PLATFORMS} {tmdb_details['platforms_line']}")
                message = "\n".join(message_lines)
                await event.edit(
                    message,
                    buttons=buttons,
                    parse_mode='html'
                )
            else:
                await event.edit(
                    FALLBACK_SEARCH_RESULT_MESSAGE.format(query=query),
                    buttons=buttons,
                    parse_mode='html'
                )
        except errors.MessageNotModifiedError:
            pass

    elif data.startswith("filter:"):
        query, new_category, current_quality, current_category = data.split(":")[1], data.split(":")[2], data.split(":")[3], data.split(":")[4] if len(data.split(":")) > 4 else "none"
        tmdb_details = fetch_tmdb_details(query)
        clean_query = normalize_query(query)
        regex_pattern = ".*".join(re.escape(word) for word in clean_query.split())
        filter_query = {"caption": {"$regex": regex_pattern, "$options": "i"}}
        has_quality_filter = current_quality and current_quality != "none"
        has_category_filter = current_category and current_category != "none"
        if new_category == current_category and has_category_filter:
            if has_quality_filter:
                filter_query["quality"] = current_quality
                selected_category = None
            else:
                selected_category = None
        else:
            selected_category = new_category if new_category != "none" else None
            if selected_category:
                filter_query["category"] = selected_category
            if has_quality_filter:
                filter_query["quality"] = current_quality
        results = list(videos_collection.find(filter_query))
        page = 0
        per_page = 5
        total_pages = (len(results) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        buttons = []
        for doc in results[start:end]:
            caption = doc["caption"][:50] + "..." if len(doc["caption"]) > 50 else doc["caption"]
            button_text = f"[{doc['file_size']}] {caption}"
            buttons.append([Button.inline(button_text, data=f"select:{doc['_id']}")])
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(Button.inline(BUTTON_PREV, data=f"page:{query}:{page-1}:{selected_category or 'none'}:{current_quality or 'none'}"))
            nav_buttons.append(Button.inline(BUTTON_PAGE_INFO.format(page=page+1, total=total_pages), data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(Button.inline(BUTTON_NEXT, data=f"page:{query}:{page+1}:{selected_category or 'none'}:{current_quality or 'none'}"))
            buttons.append(nav_buttons)
        quality_counts = {
            "2160p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p", "category": selected_category} if selected_category else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p"}),
            "1080p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p", "category": selected_category} if selected_category else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p"}),
            "720p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p", "category": selected_category} if selected_category else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p"}),
            "480p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p", "category": selected_category} if selected_category else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p"})
        }
        quality_buttons = []
        for q, count in quality_counts.items():
            if count > 0:
                quality_buttons.append(Button.inline(f"{q}" + (BUTTON_TICK if current_quality == q else ""), data=f"quality:{query}:{q}:{selected_category or 'none'}:{current_quality or 'none'}"))
        if quality_buttons:
            buttons.append(quality_buttons)
        movie_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "movie",
            "quality": current_quality if current_quality and current_quality != "none" else {"$exists": True}
        })
        series_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "series",
            "quality": current_quality if current_quality and current_quality != "none" else {"$exists": True}
        })
        filter_buttons = []
        if movie_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_MOVIES + (BUTTON_TICK if selected_category == "movie" else ""),
                data=f"filter:{query}:movie:{current_quality or 'none'}:{selected_category or 'none'}"
            ))
        if series_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_SERIES + (BUTTON_TICK if selected_category == "series" else ""),
                data=f"filter:{query}:series:{current_quality or 'none'}:{selected_category or 'none'}"
            ))
        buttons.append(filter_buttons)
        buttons.append([Button.inline(BUTTON_CLOSE, data="close")])
        try:
            if tmdb_details:
                message_lines = [f"{EMOJI_TYPE} <b>{tmdb_details['type']}</b> :- <a href='{tmdb_details['poster_url']}'>{tmdb_details['name']}</a>"]
                if tmdb_details.get('release_line'):
                    message_lines.append(f"{EMOJI_RELEASE} {tmdb_details['release_line']}")
                if tmdb_details.get('rating_line'):
                    message_lines.append(f"{EMOJI_RATING} {tmdb_details['rating_line']}")
                if tmdb_details.get('duration_line'):
                    message_lines.append(f"{EMOJI_DURATION} {tmdb_details['duration_line']}")
                if tmdb_details.get('season_line'):
                    message_lines.append(f"{EMOJI_SEASON} {tmdb_details['season_line']}")
                if tmdb_details.get('audio_line'):
                    message_lines.append(f"{EMOJI_AUDIO} {tmdb_details['audio_line']}")
                if tmdb_details.get('genre_line'):
                    message_lines.append(f"{EMOJI_GENRE} {tmdb_details['genre_line']}")
                if tmdb_details.get('trailer_line'):
                    message_lines.append(f"{EMOJI_TRAILER} {tmdb_details['trailer_line']}")
                if tmdb_details.get('platforms_line'):
                    message_lines.append(f"{EMOJI_PLATFORMS} {tmdb_details['platforms_line']}")
                message = "\n".join(message_lines)
                await event.edit(
                    message,
                    buttons=buttons,
                    parse_mode='html'
                )
            else:
                await event.edit(
                    FALLBACK_SEARCH_RESULT_MESSAGE.format(query=query),
                    buttons=buttons,
                    parse_mode='html'
                )
        except errors.MessageNotModifiedError:
            pass

    elif data.startswith("quality:"):
        query, new_quality, current_category, current_quality = data.split(":")[1], data.split(":")[2], data.split(":")[3], data.split(":")[4] if len(data.split(":")) > 4 else None
        tmdb_details = fetch_tmdb_details(query)
        clean_query = normalize_query(query)
        regex_pattern = ".*".join(re.escape(word) for word in clean_query.split())
        filter_query = {"caption": {"$regex": regex_pattern, "$options": "i"}}
        if current_category and current_category != "none":
            filter_query["category"] = current_category
        if new_quality == current_quality:
            selected_quality = None
        else:
            filter_query["quality"] = new_quality
            selected_quality = new_quality
        results = list(videos_collection.find(filter_query))
        page = 0
        per_page = 5
        total_pages = (len(results) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        buttons = []
        for doc in results[start:end]:
            caption = doc["caption"][:50] + "..." if len(doc["caption"]) > 50 else doc["caption"]
            button_text = f"[{doc['file_size']}] {caption}"
            buttons.append([Button.inline(button_text, data=f"select:{doc['_id']}")])
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(Button.inline(BUTTON_PREV, data=f"page:{query}:{page-1}:{current_category or 'none'}:{selected_quality or 'none'}"))
            nav_buttons.append(Button.inline(BUTTON_PAGE_INFO.format(page=page+1, total=total_pages), data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(Button.inline(BUTTON_NEXT, data=f"page:{query}:{page+1}:{current_category or 'none'}:{selected_quality or 'none'}"))
            buttons.append(nav_buttons)
        quality_counts = {
            "2160p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p", "category": current_category} if current_category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "2160p"}),
            "1080p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p", "category": current_category} if current_category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "1080p"}),
            "720p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p", "category": current_category} if current_category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "720p"}),
            "480p": videos_collection.count_documents({"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p", "category": current_category} if current_category != "none" else {"caption": {"$regex": regex_pattern, "$options": "i"}, "quality": "480p"})
        }
        quality_buttons = []
        for q, count in quality_counts.items():
            if count > 0:
                quality_buttons.append(Button.inline(f"{q}" + (BUTTON_TICK if selected_quality == q else ""), data=f"quality:{query}:{q}:{current_category or 'none'}:{selected_quality or 'none'}"))
        if quality_buttons:
            buttons.append(quality_buttons)
        movie_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "movie",
            "quality": selected_quality if selected_quality and selected_quality != "none" else {"$exists": True}
        })
        series_count = videos_collection.count_documents({
            "caption": {"$regex": regex_pattern, "$options": "i"},
            "category": "series",
            "quality": selected_quality if selected_quality and selected_quality != "none" else {"$exists": True}
        })
        filter_buttons = []
        if movie_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_MOVIES + (BUTTON_TICK if current_category == "movie" else ""),
                data=f"filter:{query}:movie:{selected_quality or 'none'}:{current_category or 'none'}"
            ))
        if series_count > 0:
            filter_buttons.append(Button.inline(
                BUTTON_SERIES + (BUTTON_TICK if current_category == "series" else ""),
                data=f"filter:{query}:series:{selected_quality or 'none'}:{current_category or 'none'}"
            ))
        buttons.append(filter_buttons)
        buttons.append([Button.inline(BUTTON_CLOSE, data="close")])
        try:
            if tmdb_details:
                message_lines = [f"{EMOJI_TYPE} <b>{tmdb_details['type']}</b> :- <a href='{tmdb_details['poster_url']}'>{tmdb_details['name']}</a>"]
                if tmdb_details.get('release_line'):
                    message_lines.append(f"{EMOJI_RELEASE} {tmdb_details['release_line']}")
                if tmdb_details.get('rating_line'):
                    message_lines.append(f"{EMOJI_RATING} {tmdb_details['rating_line']}")
                if tmdb_details.get('duration_line'):
                    message_lines.append(f"{EMOJI_DURATION} {tmdb_details['duration_line']}")
                if tmdb_details.get('season_line'):
                    message_lines.append(f"{EMOJI_SEASON} {tmdb_details['season_line']}")
                if tmdb_details.get('audio_line'):
                    message_lines.append(f"{EMOJI_AUDIO} {tmdb_details['audio_line']}")
                if tmdb_details.get('genre_line'):
                    message_lines.append(f"{EMOJI_GENRE} {tmdb_details['genre_line']}")
                if tmdb_details.get('trailer_line'):
                    message_lines.append(f"{EMOJI_TRAILER} {tmdb_details['trailer_line']}")
                if tmdb_details.get('platforms_line'):
                    message_lines.append(f"{EMOJI_PLATFORMS} {tmdb_details['platforms_line']}")
                message = "\n".join(message_lines)
                await event.edit(
                    message,
                    buttons=buttons,
                    parse_mode='html'
                )
            else:
                await event.edit(
                    FALLBACK_SEARCH_RESULT_MESSAGE.format(query=query),
                    buttons=buttons,
                    parse_mode='html'
                )
        except errors.MessageNotModifiedError:
            pass

    elif data.startswith("post_yes:"):
        encoded_movie = data.split(":", 1)[1]
        sender = await event.get_sender()
        if sender.id != admin_id:
            return
        deep_link = f"https://t.me/{BOT_USERNAME}?start={encoded_movie}"
        await event.edit(POST_CONTENT_PROMPT_MESSAGE, parse_mode='html')
        
        @client.on(events.NewMessage(from_users=admin_id))
        async def handle_post_content(post_event):
            if post_event.is_private:
                buttons = [[Button.url(DEEP_LINK_BUTTON, deep_link)]]
                await client.send_message(
                    MAIN_CHANNEL_ID,
                    message=post_event.message.text or "",
                    file=post_event.message.media,
                    buttons=buttons,
                    parse_mode='html'
                )
                await post_event.reply(POST_SENT_MESSAGE, parse_mode='html')
                client.remove_event_handler(handle_post_content)

    elif data == "post_no":
        await event.edit(POST_CANCELLED_MESSAGE, parse_mode='html')

    elif data == "close":
        await event.edit(CLOSED_MESSAGE, parse_mode='html')

    elif data == "noop":
        await event.answer()