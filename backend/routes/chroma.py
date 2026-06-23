"""
ChromaDB API routes.
"""
from fastapi import APIRouter
from services.chroma_client import chroma_client


router = APIRouter()


@router.get("/api/chroma/status")
async def get_chroma_status():
    """
    Returns ChromaDB connection status.
    """
    try:
        status = chroma_client.get_status()
        return {
            "status": "connected" if status else "disconnected",
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
        collections = []
        for game in GAME_CONFIGS.keys():
            count = chroma_client.count_documents(game)
            collections.append({
                "name": game,
                "count": count
            })
        return {
            "status": "ok",
            "collections": collections
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }