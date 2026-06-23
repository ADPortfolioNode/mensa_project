"""
Experiments API routes.
"""
from fastapi import APIRouter
from experiments.store import ExperimentStore


router = APIRouter()
exp_store = ExperimentStore()


@router.get("/api/experiments")
async def get_experiments():
    """
    Returns list of all completed experiments.
    """
    try:
        experiments = exp_store.list_experiments()
        return {
            "status": "ok",
            "experiments": experiments,
            "count": len(experiments)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }