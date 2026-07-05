"""
Predictions API routes.
"""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from services.predictor import predictor_service
from experiments.store import ExperimentStore
from utils.validation import _require_game_key
from config import GAME_PREDICTION_SCHEDULES


router = APIRouter()
exp_store = ExperimentStore("/data/experiments/experiments.json")


class PredictionRequest(BaseModel):
    game: str
    recent_k: int = 10


@router.get("/api/predictions/all")
async def get_all_predictions():
    """
    Returns summary of available predictions across all games.
    """
    try:
        from config import GAME_CONFIGS
        
        predictions_summary = []
        for game in GAME_CONFIGS.keys():
            # Check if model exists for this game
            try:
                summary = predictor_service.get_prediction_summary(game)
                predictions_summary.append({
                    "game": game,
                    "has_model": summary.get("has_model", False),
                    "last_prediction": summary.get("last_prediction"),
                    "model_accuracy": summary.get("accuracy")
                })
            except Exception:
                predictions_summary.append({
                    "game": game,
                    "has_model": False
                })
        
        return {
            "status": "ok",
            "predictions": predictions_summary
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/api/predict")
async def make_prediction(request: PredictionRequest):
    """
    Generate prediction for a specific game using recent history.
    """
    try:
        game_key = _require_game_key(request.game)
        timestamp = datetime.now().timestamp()
        
        def _run_prediction():
            if hasattr(predictor_service, "predict_next_draw"):
                return predictor_service.predict_next_draw(game_key, request.recent_k)
            if hasattr(predictor_service, "predict"):
                return predictor_service.predict(game_key, request.recent_k)
            raise RuntimeError("PredictorService is missing predict_next_draw/predict methods")

        result = await asyncio.to_thread(_run_prediction)

        if result.get("status") == "error":
            return {
                "status": "error",
                "game": game_key,
                "message": result.get("message", "Suggestion failed."),
            }

        # Calculate next draw date
        tz = None  # Use local timezone
        dt = datetime.now(tz) if tz else datetime.now()
        schedule = GAME_PREDICTION_SCHEDULES.get(game_key, {})
        
        # Find next draw date (simple: next day with >0 draws)
        next_draw_date = None
        for offset in range(1, 8):
            candidate = dt + timedelta(days=offset)
            weekday = candidate.weekday()
            daily = int(schedule.get("daily_draws", 0) or 0)
            weekday_draws = schedule.get("weekday_draws", {})
            draws = int(weekday_draws.get(weekday, daily) or 0)
            if draws > 0:
                next_draw_date = candidate.date().isoformat()
                break

        exp_store.save_experiment({
            "experiment_id": f"predict-{game_key}-{int(timestamp)}",
            "game": game_key,
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "prediction",
            "recent_k": request.recent_k,
            "prediction": result,
            "next_draw_date": next_draw_date,
        })
        
        return {
            **result,
            "status": "COMPLETED",
            "game": game_key,
            "next_draw_date": next_draw_date,
            "highest_accuracy": result.get("highest_accuracy"),
            "model_metadata": result.get("model_metadata"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }