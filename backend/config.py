import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DATASET_ENDPOINTS = {
    "take5": ["https://data.ny.gov/api/views/6wrc-wmqa/rows.json"],
    "pick3": ["https://data.ny.gov/api/views/n4w8-wxte/rows.json"],
    "powerball": ["https://data.ny.gov/api/views/d6yy-54nr/rows.json"],

    "megamillions": ["https://data.ny.gov/api/views/5xaw-6ayf/rows.json"],
    "pick10": ["https://data.ny.gov/api/views/bycu-cw7c/rows.json"],
    "cash4life": ["https://data.ny.gov/api/views/kwxv-fwze/rows.json"],
    "quickdraw": ["https://data.ny.gov/api/views/7sqk-ycpk/rows.json"],
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
    "powerball": {
        "name": "Powerball",
        "url": "https://data.ny.gov/Government-Finance/Lottery-Powerball-Winning-Numbers-Beginning-2010/d6yy-54nr",
    },

    "megamillions": {
        "name": "Mega Millions",
        "url": "https://data.ny.gov/Government-Finance/Lottery-Mega-Millions-Winning-Numbers-Beginning-20/5xaw-6ayf",
    },
    "pick10": {
        "name": "Pick 10",
        "url": "https://data.ny.gov/Government-Finance/Lottery-Pick-10-Winning-Numbers-Beginning-1987/bycu-cw7c",
    },
    "cash4life": {
        "name": "Cash 4 Life",
        "url": "https://data.ny.gov/Government-Finance/Lottery-Cash-4-Life-Winning-Numbers/kwxv-fwze",
    },
    "quickdraw": {
        "name": "Quick Draw",
        "url": "https://data.ny.gov/Government-Finance/Lottery-Quick-Draw-Winning-Numbers-Beginning-2013/7sqk-ycpk",
    },
}
