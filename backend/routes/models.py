"""
Models API routes.
"""
from fastapi import APIRouter, HTTPException
from config import GAME_CONFIGS
from utils.model_utils import _load_model_metadata


router = APIRouter()


@router.get("/api/models/{game}/metadata")
async def get_model_metadata(game: str):
    """
    Returns persisted model artifact metadata for a specific game.
    """
    try:
        from utils.validation import _require_game_key
        game_key = _require_game_key(game)
        metadata = _load_model_metadata(game_key)
        return {
            "status": "ok",
            "metadata": metadata,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "game": game,
            "message": str(e)
        }


@router.get("/api/models/metadata")
async def get_all_model_metadata():
    """
    Returns persisted model artifact metadata for all configured games.
    """
    all_metadata = [_load_model_metadata(game_key) for game_key in GAME_CONFIGS.keys()]
    return {
        "status": "ok",
        "models": all_metadata,
    }