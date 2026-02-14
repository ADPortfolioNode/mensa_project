from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for the application.
    """
    PROJECT_NAME: str = "Mensa Project"
    
    # OpenAI
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROK_API_KEY: str | None = None
    GROK_API_BASE: str = "https://api.x.ai/v1"
    GROK_MODEL: str = "grok-3-mini-beta"
    
    # ChromaDB
    CHROMA_HOST: str = "mensa_chroma"
    CHROMA_PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()

# Game configurations (imported by main.py)
GAME_CONFIGS = {
    "take5": {
        "primary_count": 5,
        "primary_min": 1,
        "primary_max": 39,
        "primary_unique": True,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 39,
        "bonus_keys": ["midday_bonus", "evening_bonus", "bonus"],
    },
    "pick3": {
        "primary_count": 3,
        "primary_min": 0,
        "primary_max": 9,
        "primary_unique": False,
        "bonus_count": 0,
    },
    "powerball": {
        "primary_count": 5,
        "primary_min": 1,
        "primary_max": 69,
        "primary_unique": True,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 26,
        "embedded_bonus_in_winning_numbers": True,
        "bonus_keys": ["powerball", "power_ball"],
    },
    "megamillions": {
        "primary_count": 5,
        "primary_min": 1,
        "primary_max": 70,
        "primary_unique": True,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 25,
        "bonus_keys": ["mega_ball", "megaball"],
    },
    "pick10": {
        "primary_count": 20,
        "primary_min": 1,
        "primary_max": 80,
        "primary_unique": True,
        "bonus_count": 0,
    },
    "cash4life": {
        "primary_count": 5,
        "primary_min": 1,
        "primary_max": 60,
        "primary_unique": True,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 4,
        "bonus_keys": ["cash_ball", "cashball"],
    },
    "quickdraw": {
        "primary_count": 20,
        "primary_min": 1,
        "primary_max": 80,
        "primary_unique": True,
        "bonus_count": 0,
    },
    "nylotto": {
        "primary_count": 6,
        "primary_min": 1,
        "primary_max": 59,
        "primary_unique": True,
        "bonus_count": 1,
        "bonus_min": 1,
        "bonus_max": 59,
        "bonus_keys": ["bonus"],
    }
}

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