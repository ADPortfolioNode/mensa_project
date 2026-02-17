from pydantic_settings import BaseSettings, SettingsConfigDict
import re

class Settings(BaseSettings):
    """
    Centralized configuration for the application.
    """
    PROJECT_NAME: str = "Mensa Project"
    
    # OpenAI
    OPENAI_API_KEY: str | None = None
    CHAT_GPT_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    
    # ChromaDB
    CHROMA_HOST: str = "mensa_chroma"
    CHROMA_PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()

# Game configurations (imported by main.py)
GAME_CONFIGS = {
    "take5": {},
    "pick3": {},
    "powerball": {},
    "megamillions": {},
    "pick10": {},
    "cash4life": {},
    "quickdraw": {},
    "nylotto": {}
}

GAME_TITLES = {
    "take5": "Take 5",
    "pick3": "Pick 3",
    "powerball": "Powerball",
    "megamillions": "Mega Millions",
    "pick10": "Pick 10",
    "cash4life": "Cash4Life",
    "quickdraw": "Quick Draw",
    "nylotto": "NY Lotto",
}

GAME_ALIASES = {
    "take5": ["take 5", "take-five"],
    "pick3": ["pick 3", "pick-three"],
    "powerball": ["power ball"],
    "megamillions": ["mega millions", "mega-millions"],
    "pick10": ["pick 10", "pick-ten"],
    "cash4life": ["cash 4 life", "cash-for-life", "cash for life"],
    "quickdraw": ["quick draw", "quick-draw"],
    "nylotto": ["ny lotto", "new york lotto", "newyorklotto"],
}

GAME_PREDICTION_FORMATS = {
    "take5": {
        "main_count": 5,
        "main_min": 1,
        "main_max": 39,
        "bonus_count": 0,
        "unique_main": True,
        "sort_main": True,
        "main_label": "Numbers",
    },
    "pick3": {
        "main_count": 3,
        "main_min": 0,
        "main_max": 9,
        "bonus_count": 0,
        "unique_main": False,
        "sort_main": False,
        "main_label": "Digits",
    },
    "powerball": {
        "main_count": 5,
        "main_min": 1,
        "main_max": 69,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 26,
        "unique_main": True,
        "sort_main": True,
        "main_label": "White Balls",
        "bonus_label": "Powerball",
    },
    "megamillions": {
        "main_count": 5,
        "main_min": 1,
        "main_max": 70,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 25,
        "unique_main": True,
        "sort_main": True,
        "main_label": "White Balls",
        "bonus_label": "Mega Ball",
    },
    "pick10": {
        "main_count": 10,
        "main_min": 1,
        "main_max": 80,
        "bonus_count": 0,
        "unique_main": True,
        "sort_main": True,
        "main_label": "Numbers",
    },
    "cash4life": {
        "main_count": 5,
        "main_min": 1,
        "main_max": 60,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 4,
        "unique_main": True,
        "sort_main": True,
        "main_label": "White Balls",
        "bonus_label": "Cash Ball",
    },
    "quickdraw": {
        "main_count": 20,
        "main_min": 1,
        "main_max": 80,
        "bonus_count": 0,
        "unique_main": True,
        "sort_main": True,
        "main_label": "Numbers",
    },
    "nylotto": {
        "main_count": 6,
        "main_min": 1,
        "main_max": 59,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 59,
        "unique_main": True,
        "sort_main": True,
        "main_label": "Main Numbers",
        "bonus_label": "Bonus Number",
    },
}


def _normalize_game_token(value: str | None) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())
    return normalized


def resolve_game_key(value: str | None) -> str | None:
    token = _normalize_game_token(value)
    if not token:
        return None

    for game_key in GAME_CONFIGS.keys():
        if _normalize_game_token(game_key) == token:
            return game_key

    for game_key, title in GAME_TITLES.items():
        if _normalize_game_token(title) == token:
            return game_key

    for game_key, aliases in GAME_ALIASES.items():
        for alias in aliases:
            if _normalize_game_token(alias) == token:
                return game_key

    return None

DATASET_ENDPOINTS = {
    "take5": ["https://data.ny.gov/api/views/dg63-4siq/rows.json?accessType=DOWNLOAD"],
    "pick3": ["https://data.ny.gov/api/views/fore-yqye/rows.json?accessType=DOWNLOAD"],
    "powerball": ["https://data.ny.gov/api/views/d6yy-54nr/rows.json?accessType=DOWNLOAD"],
    "megamillions": ["https://data.ny.gov/api/views/5xaw-6ayf/rows.json?accessType=DOWNLOAD"],
    "pick10": ["https://data.ny.gov/api/views/bycu-cw7c/rows.json?accessType=DOWNLOAD"],
    "cash4life": ["https://data.ny.gov/api/views/kwxv-fwze/rows.json?accessType=DOWNLOAD"],
    "quickdraw": ["https://data.ny.gov/api/views/7sqk-ycpk/rows.json?accessType=DOWNLOAD"],
    "nylotto": ["https://data.ny.gov/api/views/6nbc-h7bj/rows.json?accessType=DOWNLOAD"]
}