from datetime import datetime, timedelta
from telethon import TelegramClient, Button
from database import get_user, update_user_subscription
from utils import get_current_datetime, logger
from config import TRIAL_ACTIVATED_MESSAGE, SUBSCRIPTION_INACTIVE_MESSAGE, SUBSCRIPTION_EXPIRED_MESSAGE, BUTTON_RECHARGE, SUBSCRIPTION_EXPIRED_ADMIN_MESSAGE, ADMIN_ID

async def check_and_handle_subscription(client: TelegramClient, event, user_id: int, users_collection, file_message):
    user = get_user(users_collection, user_id)
    current_datetime = get_current_datetime()

    if "is_paid" not in user:
        logger.info(f"Activating 7-day free trial for user {user_id}")
        expiry_date = current_datetime + timedelta(days=7)
        update_user_subscription(
            users_collection,
            user_id,
            {
                "paid_duration": 7,
                "is_paid": True,
                "plan_description": "7-Days Free Trial",
                "expiry_date": expiry_date
            }
        )
        await client.send_message(user_id, TRIAL_ACTIVATED_MESSAGE, parse_mode='html')
        await client.send_message(
            user_id,
            message=file_message.text or "",
            file=file_message.media
        )
    else:
        if not user["is_paid"]:
            logger.info(f"User {user_id} has inactive subscription")
            await client.send_message(
                user_id,
                SUBSCRIPTION_INACTIVE_MESSAGE,
                buttons=[Button.inline(BUTTON_RECHARGE, data="recharge")],
                parse_mode='html'
            )
        else:
            expiry_date = user["expiry_date"]
            if current_datetime <= expiry_date:
                logger.info(f"User {user_id} has active subscription, sending file")
                await client.send_message(
                    user_id,
                    message=file_message.text or "",
                    file=file_message.media
                )
            else:
                logger.info(f"User {user_id} subscription expired on {expiry_date}")
                # Capture the plan description before updating it
                expired_plan = user.get("plan_description", "Unknown Plan")
                update_user_subscription(
                    users_collection,
                    user_id,
                    {
                        "is_paid": False,
                        "paid_duration": 0,
                        "plan_description": "Plan Expired"
                    }
                )
                # Notify user
                await client.send_message(
                    user_id,
                    SUBSCRIPTION_EXPIRED_MESSAGE.format(expiry_date=expiry_date.strftime("%Y-%m-%d %H:%M:%S")),
                    buttons=[Button.inline(BUTTON_RECHARGE, data="recharge")],
                    parse_mode='html'
                )
                # Notify admin instantly with plan details
                await client.send_message(
                    ADMIN_ID,
                    SUBSCRIPTION_EXPIRED_ADMIN_MESSAGE.format(
                        user_id=user_id,
                        expiry_date=expiry_date.strftime("%Y-%m-%d %H:%M:%S"),
                        plan_description=expired_plan
                    ),
                    parse_mode='html'
                )