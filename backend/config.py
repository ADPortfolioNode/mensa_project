import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DATASET_ENDPOINTS = {
    "take5": ["https://data.ny.gov/api/views/6wrc-wmqa/rows.json"],
    "pick3": ["https://data.ny.gov/api/views/n4w8-wxte/rows.json"],
}

GAME_CONFIGS = {
    "take5": {
        "name": "Take 5",
        "url": "https://data.ny.gov/Government-Finance/Take-5-Lottery-Winning-Numbers/6wrc-wmqa",
    },
    "pick3": {
        "name": "Pick 3",
        "url": "https://data.ny.gov/Government-Finance/Pick-3-Lottery-Winning-Numbers/n4w8-wxte",
    },
}
