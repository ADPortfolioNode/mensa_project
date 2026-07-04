"""
Games API routes.
"""
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from config import GAME_CONFIGS, GAME_TITLES, resolve_game_key
from services.chroma_client import chroma_client
from utils.validation import _require_game_key


router = APIRouter()

CHROMA_QUERY_TIMEOUT = 8.0


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


@router.get("/api/games/summaries")
async def get_all_game_summaries():
    """
    Return draw counts for all games in one non-blocking request.
    """
    game_names = list(GAME_CONFIGS.keys())
    snapshots = await asyncio.to_thread(
        chroma_client.get_collections_snapshot,
        game_names,
        CHROMA_QUERY_TIMEOUT,
    )
    summaries = {
        snap["name"]: {
            "game": snap["name"],
            "draw_count": int(snap.get("count") or 0),
        }
        for snap in snapshots
    }
    for game in game_names:
        summaries.setdefault(game, {"game": game, "draw_count": 0})
    return {"summaries": summaries}


@router.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    """
    Get summary statistics for a specific game.
    """
    game_key = _require_game_key(game)
    try:
        draw_count = await asyncio.wait_for(
            asyncio.to_thread(chroma_client.count_documents, game_key),
            timeout=CHROMA_QUERY_TIMEOUT,
        )
    except asyncio.TimeoutError:
        draw_count = 0
    return GameSummaryResponse(game=game_key, draw_count=draw_count)