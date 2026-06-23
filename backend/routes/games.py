"""
Games API routes.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from config import GAME_CONFIGS, GAME_TITLES, resolve_game_key
from services.chroma_client import chroma_client
from utils.validation import _require_game_key


router = APIRouter()


class GameSummaryResponse(BaseModel):
    game: str
    draw_count: int


@router.get("/api/games")
async def get_games():
    """
    Returns list of available games for ingestion.
    """
    game_names = list(GAME_CONFIGS.keys())
    return {
        "games": game_names,
        "titles": {game: GAME_TITLES.get(game, game) for game in game_names},
    }


@router.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    """
    Get summary statistics for a specific game.
    """
    game_key = _require_game_key(game)
    draw_count = chroma_client.count_documents(game_key)
    return GameSummaryResponse(game=game_key, draw_count=draw_count)