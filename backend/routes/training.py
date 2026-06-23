"""
Training API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.trainer import trainer_service
from experiments.store import ExperimentStore
from utils.validation import _require_game_key
from datetime import datetime


router = APIRouter()
exp_store = ExperimentStore()


class TrainingRequest(BaseModel):
    game: str
    target_accuracy: float = 0.98
    max_iterations: int = 100


@router.post("/api/train")
async def train_model(request: TrainingRequest):
    """
    Train a prediction model for a specific game.
    """
    try:
        game_key = _require_game_key(request.game)
        timestamp = datetime.now().timestamp()
        
        result = trainer_service.train(
            game_key,
            target_accuracy=request.target_accuracy,
            max_iterations=request.max_iterations
        )
        
        # Save experiment record
        exp_store.save_experiment({
            "experiment_id": f"train-{game_key}-{int(timestamp)}",
            "game": game_key,
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "training",
            "target_accuracy": request.target_accuracy,
            "final_accuracy": result.get("accuracy"),
            "iterations": result.get("iterations"),
            "training_time": result.get("training_time")
        })
        
        return {
            "status": "COMPLETED",
            "game": game_key,
            "experiment_id": f"train-{game_key}-{int(timestamp)}",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }