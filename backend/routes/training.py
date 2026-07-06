"""
Training API routes.
"""
import asyncio
import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from services.trainer import trainer_service
from experiments.store import ExperimentStore
from utils.training_params import extract_training_params, merge_training_params
from utils.validation import _require_game_key
from config import GAME_CONFIGS
from services.chroma_client import chroma_client
from utils.timestamps import normalize_experiment_record, runtime_timestamp_fields


router = APIRouter()
exp_store = ExperimentStore("/data/experiments/experiments.json")


class TrainingRequest(BaseModel):
    game: str
    target_accuracy: float = Field(default=0.90, ge=0.5, le=0.99)
    max_iterations: int = Field(default=40, ge=1, le=100)
    train_size: float = Field(default=0.25, ge=0.10, le=0.50)
    n_estimators: int = Field(default=250, ge=50, le=600)
    max_depth: int = Field(default=18, ge=4, le=32)
    random_state: int = Field(default=42, ge=0)
    window_size: int = Field(default=3, ge=1, le=8)
    auto_tune: bool = True
    blend_step: float | None = Field(default=None, ge=0.01, le=0.5)

    @field_validator("target_accuracy", mode="before")
    @classmethod
    def clamp_target_accuracy(cls, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return value
        return min(0.99, max(0.5, numeric))


class TrainAllRequest(BaseModel):
    games: list[str] | None = None
    target_accuracy: float = Field(default=0.90, ge=0.5, le=0.99)
    max_iterations: int = Field(default=40, ge=1, le=100)
    train_size: float = Field(default=0.25, ge=0.10, le=0.50)
    n_estimators: int = Field(default=250, ge=50, le=600)
    max_depth: int = Field(default=18, ge=4, le=32)
    random_state: int = Field(default=42, ge=0)
    window_size: int = Field(default=3, ge=1, le=8)
    auto_tune: bool = True


def _dataset_snapshot(game: str) -> dict:
    try:
        count = chroma_client.count_documents(game)
        return {
            "dataset_hash": hashlib.md5(f"{game}|{count}".encode("utf-8")).hexdigest(),
            "record_count": int(count or 0),
        }
    except Exception:
        return {"dataset_hash": None, "record_count": 0}


@router.get("/api/train_settings")
async def get_train_settings(game: str = None):
    defaults = trainer_service.get_training_defaults()
    defaults["blend_step"] = float(trainer_service.blend_step)

    if game:
        game_key = _require_game_key(game)
        incremental = trainer_service.get_incremental_training_context(
            game_key,
            requested_target=defaults["target_accuracy"],
        )
        recreate_defaults = incremental.get("recreate_defaults") or {}
        merged_defaults = {
            **defaults,
            **{key: value for key, value in recreate_defaults.items() if value is not None},
        }
        return {
            "game": game_key,
            "defaults": merged_defaults,
            "dataset": _dataset_snapshot(game_key),
            "incremental": incremental,
            "best_training_params": incremental.get("best_training_params") or {},
            "recreate_defaults": recreate_defaults,
        }

    per_game = {}
    for game_name in GAME_CONFIGS.keys():
        incremental = trainer_service.get_incremental_training_context(
            game_name,
            requested_target=defaults["target_accuracy"],
        )
        per_game[game_name] = {
            **_dataset_snapshot(game_name),
            "highest_accuracy": incremental.get("highest_accuracy"),
            "best_training_params": incremental.get("best_training_params") or {},
            "recreate_defaults": incremental.get("recreate_defaults") or {},
            "score_leaderboard": incremental.get("score_leaderboard") or [],
        }
    return {"game": None, "defaults": defaults, "per_game": per_game}


@router.get("/api/train_settings/{game}")
async def get_train_settings_by_path(game: str):
    return await get_train_settings(game=game)


@router.post("/api/train")
async def train_model(request: TrainingRequest):
    """
    Train a suggestion model for a specific game.
    """
    try:
        game_key = _require_game_key(request.game)

        def _run_training():
            if hasattr(trainer_service, "train"):
                return trainer_service.train(
                    game_key,
                    target_accuracy=request.target_accuracy,
                    max_iterations=request.max_iterations,
                    train_size=request.train_size,
                    n_estimators=request.n_estimators,
                    max_depth=request.max_depth,
                    random_state=request.random_state,
                    blend_step=request.blend_step,
                    window_size=request.window_size,
                    auto_tune=request.auto_tune,
                )
            if hasattr(trainer_service, "train_model"):
                trainer_service.configure_training(
                    target_accuracy=request.target_accuracy,
                    max_iterations=request.max_iterations,
                    train_size=request.train_size,
                    n_estimators=request.n_estimators,
                    max_depth=request.max_depth,
                    random_state=request.random_state,
                    window_size=request.window_size,
                    auto_tune=request.auto_tune,
                    blend_step=request.blend_step,
                )
                return trainer_service.train_model(game_key)
            raise RuntimeError("TrainerService is missing train/train_model methods")

        result = await asyncio.to_thread(_run_training)

        if result.get("status") == "error":
            return {
                "status": "error",
                "game": game_key,
                "message": result.get("message", "Training failed."),
                "accuracy": result.get("highest_accuracy") or result.get("record_accuracy"),
                "highest_accuracy": result.get("highest_accuracy"),
                "record_accuracy": result.get("record_accuracy"),
                "baseline_accuracy": result.get("baseline_accuracy"),
                "candidate_accuracy": result.get("candidate_accuracy"),
                "previous_accuracy": result.get("previous_accuracy"),
                "training_target": result.get("training_target"),
                "target_accuracy": result.get("target_accuracy"),
                "retained_previous_model": result.get("retained_previous_model"),
                "used_previous_training": result.get("used_previous_training"),
                "training_time": result.get("training_time"),
                "leaderboard": result.get("leaderboard", []),
                "accuracy_history": result.get("accuracy_history", []),
                "optimal_config_applied": result.get("optimal_config_applied", False),
                "optimal_config": result.get("optimal_config", {}),
            }

        accuracy = (
            result.get("highest_accuracy")
            or result.get("record_accuracy")
            or result.get("accuracy")
        )
        runtime_ts = runtime_timestamp_fields()
        experiment_id = f"train-{game_key}-{runtime_ts['timestamp_seconds']}"

        scored_params = merge_training_params(
            result.get("best_training_params"),
            result.get("training_params"),
            extract_training_params(request.model_dump()),
            {
                "train_size": result.get("train_size", request.train_size),
                "validation_size": result.get("validation_size"),
                "n_estimators": request.n_estimators,
                "max_depth": request.max_depth,
                "random_state": request.random_state,
                "window_size": request.window_size,
                "auto_tune": request.auto_tune,
                "blend_step": request.blend_step,
                "max_iterations": request.max_iterations,
                "target_accuracy": result.get("target_accuracy", request.target_accuracy),
                "training_target": result.get("training_target"),
                "model_strategy": result.get("model_strategy"),
                "blend_weight": result.get("blend_weight"),
            },
        )
        exp_store.save_experiment(normalize_experiment_record({
            "experiment_id": experiment_id,
            "game": game_key,
            **runtime_ts,
            "status": "COMPLETED",
            "type": "training",
            "target_accuracy": result.get("target_accuracy", request.target_accuracy),
            "training_target": result.get("training_target"),
            "baseline_accuracy": result.get("baseline_accuracy"),
            "final_accuracy": accuracy,
            "highest_accuracy": result.get("highest_accuracy", accuracy),
            "record_accuracy": result.get("record_accuracy", result.get("highest_accuracy", accuracy)),
            "score": result.get("highest_accuracy", accuracy),
            "accuracy": result.get("highest_accuracy", accuracy),
            "iterations": result.get("attempts"),
            "max_iterations": scored_params.get("max_iterations", request.max_iterations),
            "training_time": result.get("training_time"),
            "model_strategy": result.get("model_strategy"),
            "blend_weight": result.get("blend_weight"),
            "candidate_accuracy": result.get("candidate_accuracy"),
            "previous_accuracy": result.get("previous_accuracy"),
            "retained_previous_model": result.get("retained_previous_model"),
            "used_previous_training": result.get("used_previous_training"),
            "message": result.get("message"),
            "train_size": scored_params.get("train_size", result.get("train_size", request.train_size)),
            "validation_size": scored_params.get("validation_size", result.get("validation_size")),
            "n_estimators": scored_params.get("n_estimators", request.n_estimators),
            "max_depth": scored_params.get("max_depth", request.max_depth),
            "random_state": scored_params.get("random_state", request.random_state),
            "window_size": scored_params.get("window_size", request.window_size),
            "auto_tune": scored_params.get("auto_tune", request.auto_tune),
            "blend_step": scored_params.get("blend_step", request.blend_step),
            "data_limit": scored_params.get("data_limit"),
            "training_params": scored_params,
            "best_training_params": result.get("best_training_params") or scored_params,
            "leaderboard": result.get("leaderboard", []),
            "accuracy_history": result.get("accuracy_history", []),
            "optimal_config_applied": result.get("optimal_config_applied", False),
            "optimal_config": result.get("optimal_config", {}),
        }))

        return {
            **result,
            "status": "COMPLETED",
            "game": game_key,
            "experiment_id": experiment_id,
            "score": accuracy,
            "accuracy": accuracy,
            "highest_accuracy": result.get("highest_accuracy", accuracy),
            "record_accuracy": result.get("record_accuracy", accuracy),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }


@router.post("/api/train_all")
async def train_all_models(request: TrainAllRequest):
    try:
        trainer_service.configure_training(
            target_accuracy=request.target_accuracy,
            max_iterations=request.max_iterations,
            train_size=request.train_size,
            n_estimators=request.n_estimators,
            max_depth=request.max_depth,
            random_state=request.random_state,
            window_size=request.window_size,
            auto_tune=request.auto_tune,
        )

        game_keys = None
        if request.games:
            game_keys = [_require_game_key(game) for game in request.games]

        results = await asyncio.to_thread(trainer_service.train_all_games, game_keys)
        completed = [item for item in results if str(item.get("status", "")).lower() in ("success", "completed")]
        return {
            "status": "COMPLETED",
            "trained": len(completed),
            "total": len(results),
            "results": results,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}