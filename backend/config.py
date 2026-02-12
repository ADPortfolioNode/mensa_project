from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for the application.
    """
    PROJECT_NAME: str = "Mensa Project"
    
    # OpenAI
    OPENAI_API_KEY: str | None = None
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

DATASET_ENDPOINTS = {
    "take5": ["https://data.ny.gov/api/views/dg63-4siq/rows.json?accessType=DOWNLOAD"],
    "pick3": ["https://data.ny.gov/api/views/hsys-3def/rows.json?accessType=DOWNLOAD"],
    "powerball": ["https://data.ny.gov/api/views/d6yy-54nr/rows.json?accessType=DOWNLOAD"],
    "megamillions": ["https://data.ny.gov/api/views/5xaw-6ayf/rows.json?accessType=DOWNLOAD"],
    "pick10": ["https://data.ny.gov/api/views/bycu-cw7c/rows.json?accessType=DOWNLOAD"],
    "cash4life": ["https://data.ny.gov/api/views/kwxv-fwze/rows.json?accessType=DOWNLOAD"],
    "quickdraw": ["https://data.ny.gov/api/views/7sqk-ycpk/rows.json?accessType=DOWNLOAD"],
    "nylotto": ["https://data.ny.gov/api/views/6nbc-h7bj/rows.json?accessType=DOWNLOAD"]
}