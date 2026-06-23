"""
Health and status API routes.
"""
from fastapi import APIRouter
import time

router = APIRouter()


@router.get("/api")
async def api_root():
    """Root API endpoint."""
    return {"message": "Mensa Lottery Prediction API", "version": "1.0.0"}


@router.get("/api/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@router.get("/api/startup_status")
async def get_startup_status():
    """
    Returns initialization status for UI progress tracking.
    """
    from state.ingest_state import get_startup_state
    
    startup_state = get_startup_state()
    elapsed = None
    if startup_state["started_at"]:
        elapsed = (startup_state["completed_at"] or time.time()) - startup_state["started_at"]

    games_snapshot = {
        game: {
            "status": game_data.get("status"),
            "error": game_data.get("error"),
        }
        for game, game_data in (startup_state.get("games") or {}).items()
    }

    return {
        "status": startup_state.get("status"),
        "progress": float(startup_state.get("progress") or 0),
        "total": int(startup_state.get("total") or 0),
        "current_game": startup_state.get("current_game"),
        "current_task": startup_state.get("current_task"),
        "current_game_rows_fetched": int(startup_state.get("current_game_rows_fetched") or 0),
        "current_game_rows_total": int(startup_state.get("current_game_rows_total") or 0),
        "games": games_snapshot,
        "started_at": startup_state.get("started_at"),
        "completed_at": startup_state.get("completed_at"),
        "elapsed_s": elapsed,
        "available_games": list(startup_state.get("games", {}).keys()),
        "manual_mode": True,
    }


@router.post("/api/startup_init")
async def start_initialization():
    """
    Trigger background initialization/ingestion.
    """
    from state.ingest_state import get_startup_state, reset_startup_state
    from state.ingestion_worker import start_background_ingestion
    
    global _ingestion_started
    startup_state = get_startup_state()
    
    if _ingestion_started and startup_state.get("status") == "ingesting":
        return {
            "status": startup_state["status"],
            "message": "Initialization already running",
            "available_games": list(startup_state.get("games", {}).keys()),
        }

    reset_startup_state()
    _ingestion_started = True
    start_background_ingestion()

    return {
        "status": startup_state["status"],
        "message": "Initialization started",
        "available_games": list(startup_state.get("games", {}).keys()),
    }


# Global flag for ingestion status
_ingestion_started = False