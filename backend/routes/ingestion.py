"""
Ingestion API routes.
"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ingest import ingest_service
from state.ingest_state import get_manual_ingest_state, enqueue_manual_ingest
from state.manual_ingest_worker import _start_manual_ingest_worker_if_needed
from utils.validation import _require_game_key
from typing import Optional


router = APIRouter()


class IngestRequest(BaseModel):
    game: str
    force: bool = False


@router.post("/api/ingest")
async def trigger_ingestion(request: IngestRequest):
    """
    Trigger manual data ingestion for a specific game.
    """
    try:
        game_key = _require_game_key(request.game)
        
        # Enqueue the ingestion job
        seq = enqueue_manual_ingest(game_key, request.force)
        
        # Start worker if needed
        _start_manual_ingest_worker_if_needed()
        
        # Mark as queued in state
        from state.ingest_state import set_manual_ingest_state
        set_manual_ingest_state(game_key, {
            "status": "queued",
            "queued": True,
            "seq": seq
        })
        
        return {
            "status": "queued",
            "game": game_key,
            "sequence": seq,
            "message": f"Ingestion queued for {game_key}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/api/ingest_progress")
async def get_ingest_progress(game: str):
    """
    Get progress of manual ingestion for a specific game.
    """
    try:
        game_key = _require_game_key(game)
        progress = get_manual_ingest_state(game_key)
        
        if not progress:
            return {
                "status": "not_started",
                "game": game_key
            }
        
        return {
            "game": game_key,
            **progress
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/api/ingest_stream")
async def get_ingest_stream(game: str):
    """
    Server-sent events stream for ingestion progress.
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    
    try:
        game_key = _require_game_key(game)
        
        async def event_stream():
            while True:
                progress = get_manual_ingest_state(game_key)
                
                if progress:
                    status = progress.get("status", "unknown")
                    yield f"event: progress\ndata: {json.dumps(progress)}\n\n"
                    
                    if status in ["completed", "error"]:
                        yield f"event: complete\ndata: {json.dumps(progress)}\n\n"
                        break
                
                await asyncio.sleep(1)
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }