import os
from dotenv import load_dotenv

load_dotenv()

def get_env_var(name, cast=str, default=None):
    value = os.getenv(name)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable '{name}' is not set in .env")
    try:
        return cast(value)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable '{name}' must be a valid {cast.__name__}")

# Environment variables
API_ID = get_env_var("API_ID", int)
API_HASH = get_env_var("API_HASH")
BOT_TOKEN = get_env_var("BOT_TOKEN")
DATABASE_CHANNEL_ID = get_env_var("DATABASE_CHANNEL_ID", int)
ADMIN_ID = get_env_var("ADMIN_ID", int)
MONGO_URI = get_env_var("MONGO_URI")
BOT_USERNAME = get_env_var("BOT_USERNAME")
MAIN_CHANNEL_ID = get_env_var("MAIN_CHANNEL_ID", int)
TMDB_API_KEY = get_env_var("TMDB_API_KEY")
PAYMENT_ID = get_env_var("PAYMENT_ID")
QR_PHOTO_ID = get_env_var("QR_PHOTO_ID", int)

# Database configuration
DATABASE_NAME = "great"
COLLECTION_NAME = "search"
USERS_COLLECTION_NAME = "users"

# Message templates (All customizable messages moved here)
START_MESSAGE = (
    "🎬 **Namaste!** Welcome to **Great Cinemas Bot** 🎥\n\n"
    "🫵 Your one-stop solution for movies and series!\n\n🍿 Just send the name of any movie or series (like **'Bhaiyya Ji'** or **'Mirzapur'**) "
    "and I’ll find it for you in seconds! ⏩\n\n"
    "🎁 Free 7-day trial for new users!\n\n"
    "💰 Affordable plans flat **@40/month**!\n\n"
    "Let’s get started – what do you want to watch today? 😊"
)
NO_RESULTS_MESSAGE = "✖️ No results found for <b>{query}</b>.\n 🤫Our database is updated daily, so you may try again later or check your spelling."

EMOJI_TYPE = "🎬"
EMOJI_RELEASE = "📅"
EMOJI_RATING = "⭐"
EMOJI_DURATION = "⏳"
EMOJI_SEASON = "📺"
EMOJI_AUDIO = "🔊"
EMOJI_GENRE = "🎭"
EMOJI_TRAILER = "🎞️"
EMOJI_PLATFORMS = "📡"

POST_CONTENT_PROMPT_MESSAGE = "📬 Please send the post content you want to share in the main channel."

FALLBACK_SEARCH_RESULT_MESSAGE = "🔍 Search Result For <b>{query}</b>"
DELETE_CONFIRMATION = "Deleted {count} video(s) from the database and channel."
CLOSED_MESSAGE = "Closed 🔒"
PRIVACY_POLICY_MESSAGE = (
    "📜 Before using this bot, please read and accept our Privacy Policy.\n\n"
    "👉https://bit.ly/3Rd7pMi\n\n"
    "Do you agree to the terms?"
)

PRIVACY_ACCEPTED_MESSAGE = "🎉 Thank you! You've successfully accepted our privacy policy ✅"
PAYMENT_REQUEST_MESSAGE = (
"💰 Please send <b>{amount}₹</b> to the UPI ID below:\n\n"
"📌 <code>{payment_id}</code>\n\n"
"📷 After payment, upload a screenshot here for verification."
)
PAYMENT_VERIFICATION_MESSAGE = (
"🟢 Payment screenshot received!\n🕑Verifying your payment... \n🙏This may take some time, please wait.\n📍Note:- Do not send Screenshot again."
)
PAYMENT_TIMEOUT_MESSAGE = "⏳ Screenshot not received within 5 minutes. Please resend the payment screenshot to proceed."
UNKNOWN_COMMAND_MESSAGE = "⚠️ Unknown command! 🚫 Please use /start or 🔍 search for a 🎬 movie/📺 series."
LINK_NO_MOVIE_MESSAGE = "Please provide a movie name, e.g., /link Inception"
LINK_PROMPT_MESSAGE = "Generated deep link: {deep_link}\nDo you want to post this to the main channel?"
POST_SENT_MESSAGE = "Post sent to the main channel!"
POST_CANCELLED_MESSAGE = "Link generation cancelled."
PAYMENT_CONFIRMED_MESSAGE = "💳 Payment of ₹{amount} confirmed! ✅\n\n🤫 Your {days}-day subscription is now active. Enjoy! 🎉"
PAYMENT_REJECTED_MESSAGE = "❌ Payment rejected by admin. Please try again or contact @great_cinemas_support for assistance. 📞"
PAYMENT_ADMIN_CONFIRMED_MESSAGE = "Payment confirmed for User ID: <code>{user_id}</code> - ₹{amount} for {days} days."
PAYMENT_ADMIN_REJECTED_MESSAGE = "Payment rejected for User ID: <code>{user_id}</code>."
PAYMENT_ADMIN_ONLY_MESSAGE = "Only the admin can confirm or reject payments."
PAYMENT_ADMIN_REQUEST_MESSAGE = (
"📩 <b>Payment Verification Request</b>\n\n"
"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
"💰 <b>Amount:</b> ₹{amount}\n"
"📆 <b>Plan:</b> {days} days\n"
"⏳ <b>Received:</b> {timestamp}\n\n"
"👀 <i>Please review the screenshot and take action.</i>"
)
SUBSCRIPTION_EXPIRED_ADMIN_MESSAGE = "🔔 Subscription expired for User ID: <code>{user_id}</code> on {expiry_date}. Expired Plan: <b>{plan_description}</b>"
PAYMENT_CANCELLED_MESSAGE = "🚫 Payment process has been canceled. Let us know if you need any help!"
RECHARGE_PROMPT_MESSAGE = "🔔 Pick Your Subscription Plan:\n\n💡 Select a plan below to recharge and continue enjoying our services!"

# Button labels
BUTTON_PREV = "⬅️"
BUTTON_NEXT = "➡️"
BUTTON_PAGE_INFO = "📄 {page}/{total}"
BUTTON_MOVIES = "Movies"
BUTTON_SERIES = "Series"
BUTTON_CLOSE = "✖️CLOSE✖️"
BUTTON_TICK = " ☑️"
BUTTON_YES = "Yes"
BUTTON_NO = "No"
DEEP_LINK_BUTTON = "Search Now"
BUTTON_ACCEPT = "✔️ Agree & Continue ⏩"
BUTTON_RECHARGE = "🔋 Recharge ♻️"
BUTTON_CANCEL = "❌ Cancel 😔"

TRIAL_ACTIVATED_MESSAGE = "🎉 Hurray! You got a 7-day free trial! Enjoy unlimited access! 🍿"

SUBSCRIPTION_INACTIVE_MESSAGE = "⚠️ Your subscription is not active. Please recharge to continue watching."

SUBSCRIPTION_EXPIRED_MESSAGE = "⏳ Your subscription expired on {expiry_date}. Recharge now to keep enjoying your favorite movies! 🎬"

PLAN_DETAILS_MESSAGE = (
    "📢 <b>Choose a Subscription Plan:</b>\n\n"
    "💳 Select an option below to recharge and unlock unlimited access!"
)

PLAN_NO_SUBSCRIPTION = (
    "📜 <b>Your Subscription Plan</b>\n\n"
    "❌ <i>No active subscription found.</i>\n\n"
    "💡 Recharge now to enjoy movies and series without limits! 🎥"
)

PLAN_ACTIVE_SUBSCRIPTION = (
    "✅ <b>Your Subscription Plan</b>\n\n"
    "📌 <b>Plan:</b> {plan_description}\n"
    "⏳ <b>Duration:</b> {paid_duration} days\n"
    "🟢 <b>Status:</b> Active\n"
    "💰 <b>Paid:</b> Yes\n"
    "📅 <b>Expiry Date:</b> {expiry_date}\n"
    "⏳ <b>Days Remaining:</b> {remaining_days}\n\n"
    "🎬 Enjoy unlimited access to movies and series with your plan!"
)

PLAN_EXPIRED_SUBSCRIPTION = (
    "⚠️ <b>Your Subscription Plan</b>\n\n"
    "📌 <b>Plan:</b> {plan_description}\n"
    "⏳ <b>Duration:</b> {paid_duration} days\n"
    "🔴 <b>Status:</b> Expired\n"
    "💰 <b>Paid:</b> No\n"
    "📅 <b>Expiry Date:</b> {expiry_date}\n\n"
    "⚡ Your plan has expired. Recharge now to continue enjoying unlimited entertainment! 🍿"
)

POST_CONTENT_PROMPT_MESSAGE = "📬 Please send the post content you want to share in the main channel."
