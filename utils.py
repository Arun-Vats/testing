import os
import re
import base64
import requests
from dotenv import load_dotenv
from telethon import events, Button
import logging
from database import check_user_privacy_accepted, add_user
from config import PRIVACY_POLICY_MESSAGE, BUTTON_ACCEPT, EMOJI_TYPE, EMOJI_RELEASE, EMOJI_RATING, EMOJI_DURATION, EMOJI_SEASON, EMOJI_AUDIO, EMOJI_GENRE, EMOJI_TRAILER, EMOJI_PLATFORMS
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

LANGUAGE_MAP = {
    "hi": "Hindi", "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "bn": "Bengali", "pa": "Punjabi", "ml": "Malayalam", "gu": "Gujarati",
    "kn": "Kannada", "or": "Odia", "ur": "Urdu", "sa": "Sanskrit", "fa": "Persian",
    "ru": "Russian", "it": "Italian", "pt": "Portuguese", "tr": "Turkish", "ar": "Arabic"
}


def convert_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

def normalize_query(query):
    query = re.sub(r'\s+', ' ', query).strip().lower()
    query = re.sub(r'season\s+(\d+)', lambda m: f"s{int(m.group(1)):02d}", query)
    query = re.sub(r'episode\s+(\d+)', lambda m: f"e{int(m.group(1)):02d}", query)
    query = re.sub(r'(s)(\d{1})\b', lambda m: f"{m.group(1)}{int(m.group(2)):02d}", query)
    query = re.sub(r'(e)(\d{1})\b', lambda m: f"{m.group(1)}{int(m.group(2)):02d}", query)
    return query

def fetch_tmdb_details(query):
    original_query = query
    query = re.sub(r'\s+', ' ', query).strip().lower()
    
    # Extract year if present in the query (e.g., "movie title 2022")
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    year = year_match.group(1) if year_match else None
    
    # Remove year from base title if found
    base_title = query
    if year:
        base_title = re.sub(r'\b' + year + r'\b', '', base_title).strip()
    
    # Extract season/episode info
    season_match = re.search(r'(?:season\s+|s)(\d{1,2})\b', base_title)
    episode_match = re.search(r'(?:episode\s+|e)(\d{1,2})\b', base_title)
    season_num = int(season_match.group(1)) if season_match else None
    episode_num = int(episode_match.group(1)) if episode_match else None
    base_title = re.sub(r'(season\s+\d+|s\d{2}|episode\s+\d+|e\d{2}|s\d{2}e\d{2})', '', base_title).strip()

    # Multi-search without year parameter first
    search_url = f"{TMDB_BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={base_title}&region=IN&include_adult=true"
    response = requests.get(search_url)
    
    if response.status_code != 200 or not response.json().get("results"):
        # Try without region constraint
        search_url = f"{TMDB_BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={base_title}&include_adult=true"
        response = requests.get(search_url)
        
        if response.status_code != 200 or not response.json().get("results"):
            return None
    
    results = response.json()["results"]
    
    # If year is specified, filter results by that year
    if year:
        year_filtered_results = []
        for item in results:
            release_date = item.get("release_date") or item.get("first_air_date", "")
            if release_date.startswith(year):
                year_filtered_results.append(item)
        
        # If we have year-filtered results, use those instead
        if year_filtered_results:
            results = year_filtered_results
    
    # Get the first relevant result
    result = next((item for item in results if item.get("media_type") in ["movie", "tv"]), None)
    
    if not result:
        return None
        
    media_type = result["media_type"]
    name = result.get("title") or result.get("name", base_title)
    poster_path = result.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/150"
    details = {"type": "Movie" if media_type == "movie" else "Series", "name": name, "poster_url": poster_url}

    release_date = result.get("release_date") or result.get("first_air_date")
    if release_date:
        details["release_line"] = f"Release Date :- {release_date} IN"
    vote_average = result.get("vote_average")
    if vote_average:
        details["rating_line"] = f"Rating :- {round(vote_average, 1)}"

    if media_type == "movie":
        movie_details_url = f"{TMDB_BASE_URL}/movie/{result['id']}?api_key={TMDB_API_KEY}&append_to_response=release_dates"
        movie_response = requests.get(movie_details_url).json()
        runtime = movie_response.get("runtime")
        if runtime:
            hours, minutes = divmod(runtime, 60)
            details["duration_line"] = f"Duration :- {hours}h {minutes}m"
    elif media_type == "tv":
        series_details_url = f"{TMDB_BASE_URL}/tv/{result['id']}?api_key={TMDB_API_KEY}"
        series_response = requests.get(series_details_url).json()
        seasons = series_response.get("number_of_seasons")
        if seasons:
            details["season_line"] = f"Total Season :- {seasons}"
        episode_run_time = series_response.get("episode_run_time")
        if episode_run_time and episode_run_time[0]:
            details["duration_line"] = f"Avg Episode Duration :- {episode_run_time[0]}m"
        
        if season_num:
            season_url = f"{TMDB_BASE_URL}/tv/{result['id']}/season/{season_num}?api_key={TMDB_API_KEY}"
            season_response = requests.get(season_url)
            if season_response.status_code == 200:
                season_data = season_response.json()
                details["type"] = f"Series - Season {season_num}"
                details["season_line"] = f"Season {season_num} Episodes :- {len(season_data.get('episodes', []))}"
                if season_data.get("poster_path"):
                    details["poster_url"] = f"{TMDB_IMAGE_BASE_URL}{season_data['poster_path']}"
                if episode_num:
                    episode = next((ep for ep in season_data.get("episodes", []) if ep["episode_number"] == episode_num), None)
                    if episode:
                        details["type"] = f"Series - Season {season_num} Episode {episode_num}"
                        details["name"] = f"{name} - {episode['name']}"
                        details["release_line"] = f"Air Date :- {episode.get('air_date', '')} IN" if episode.get("air_date") else ""
                        details["duration_line"] = f"Duration :- {episode.get('runtime', episode_run_time[0] if episode_run_time else 0)}m"
                        if episode.get("vote_average"):
                            details["rating_line"] = f"Rating :- {round(episode['vote_average'], 1)}"

    language = result.get("original_language")
    if language:
        details["audio_line"] = f"Original Audio :- {LANGUAGE_MAP.get(language, language.upper())}"
    genres = [g["name"] for g in requests.get(f"{TMDB_BASE_URL}/{media_type}/{result['id']}?api_key={TMDB_API_KEY}").json().get("genres", [])]
    if genres:
        details["genre_line"] = f"Genre :- {' '.join(f'#{g.lower()}' for g in genres)}"
    video_url = f"{TMDB_BASE_URL}/{media_type}/{result['id']}/videos?api_key={TMDB_API_KEY}"
    video_response = requests.get(video_url).json()
    trailer_key = next((v["key"] for v in video_response.get("results", []) if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
    if trailer_key:
        details["trailer_line"] = f"Trailer :- <a href='https://www.youtube.com/watch?v={trailer_key}'>Click Here</a>"
    providers = requests.get(f"{TMDB_BASE_URL}/{media_type}/{result['id']}/watch/providers?api_key={TMDB_API_KEY}").json().get("results", {}).get("IN", {}).get("flatrate", [])
    if providers:
        provider_names = ", ".join(p["provider_name"] for p in providers)
        details["platforms_line"] = f"Platforms :- {provider_names}"
    
    # Only set default for keys that might be accessed, don't add empty strings
    for key in ["release_line", "rating_line", "duration_line", "season_line", "audio_line", "genre_line", "trailer_line", "platforms_line"]:
        details.setdefault(key, "")
    
    return details

def format_tmdb_message(details):
    lines = [f"{EMOJI_TYPE} <b>{details['type']}</b> :- <a href='{details['poster_url']}'>{details['name']}</a>"]
    
    # Only add non-empty lines
    if details.get('release_line'):
        lines.append(f"{EMOJI_RELEASE} {details['release_line']}")
    if details.get('rating_line'):
        lines.append(f"{EMOJI_RATING} {details['rating_line']}")
    if details.get('duration_line'):
        lines.append(f"{EMOJI_DURATION} {details['duration_line']}")
    if details.get('season_line'):
        lines.append(f"{EMOJI_SEASON} {details['season_line']}")
    if details.get('audio_line'):
        lines.append(f"{EMOJI_AUDIO} {details['audio_line']}")
    if details.get('genre_line'):
        lines.append(f"{EMOJI_GENRE} {details['genre_line']}")
    if details.get('trailer_line'):
        lines.append(f"{EMOJI_TRAILER} {details['trailer_line']}")
    if details.get('platforms_line'):
        lines.append(f"{EMOJI_PLATFORMS} {details['platforms_line']}")
    
    # Join all lines with a single newline
    return "\n".join(lines)

def generate_deep_link(bot_username: str, query: str) -> str:
    encoded_query = base64.urlsafe_b64encode(query.encode('utf-8')).decode('utf-8').rstrip('=')
    return f"https://t.me/{bot_username}?start={encoded_query}"

def decode_deep_link(encoded_query: str) -> str:
    padded_query = encoded_query + '=' * (4 - len(encoded_query) % 4)
    return base64.urlsafe_b64decode(padded_query.encode('utf-8')).decode('utf-8')

async def check_privacy_policy(client, event, users_collection, callback=None):
    user_id = event.sender_id
    logger.info(f"Checking privacy for user {user_id} in event {event.__class__.__name__}")
    if not check_user_privacy_accepted(users_collection, user_id):
        logger.info(f"User {user_id} not accepted, sending privacy policy")
        add_user(users_collection, user_id)
        msg = await event.reply(
            PRIVACY_POLICY_MESSAGE,
            buttons=[Button.inline(BUTTON_ACCEPT, data=f"accept_privacy:{user_id}")]
        )
        return False, msg
    logger.info(f"User {user_id} already accepted privacy policy")
    return True, None

def get_current_datetime():
    return datetime.now()

# Example of how to use the format_tmdb_message function:
# When you want to send a message with TMDB details
async def send_tmdb_info(event, query):
    details = fetch_tmdb_details(query)
    if details:
        formatted_message = format_tmdb_message(details)
        await event.reply(formatted_message, parse_mode='html')
    else:
        await event.reply(f"No results found for '{query}'")
