"""
ChromaDB API routes.
"""
import asyncio

from fastapi import APIRouter
from services.chroma_client import chroma_client


router = APIRouter()

CHROMA_QUERY_TIMEOUT = 8.0


@router.get("/api/chroma/status")
async def get_chroma_status():
    """
    Returns ChromaDB connection status.
    """
    try:
        status = await asyncio.to_thread(chroma_client.get_chroma_status)
        is_ok = status.get("status") == "ok"
        return {
            "status": "connected" if is_ok else "disconnected",
            "details": status
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/api/chroma/collections")
async def get_chroma_collections():
    """
    Returns list of ChromaDB collections with document counts.
    """
    try:
        from config import GAME_CONFIGS
        game_names = list(GAME_CONFIGS.keys())
        snapshots = await asyncio.to_thread(
            chroma_client.get_collections_snapshot,
            game_names,
            CHROMA_QUERY_TIMEOUT,
        )
        collections = [
            {
                "name": snap["name"],
                "count": int(snap.get("count") or 0),
                "state": snap.get("state", "ok"),
            }
            for snap in snapshots
        ]
        return {
            "status": "ok",
            "collections": collections
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }