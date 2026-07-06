"""Load and merge YAML prediction configs with GAME_CONFIGS."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from config import GAME_CONFIGS
from prediction.core.types import GameRules

_CONFIG_DIR = Path(__file__).resolve().parent
_GAMES_DIR = _CONFIG_DIR / "games"


class EnsembleConfig(BaseModel):
    enabled: bool = True
    initial_weights: dict[str, float] = Field(default_factory=dict)
    learning_rate: float = 0.05
    min_weight: float = 0.01


class NNConfig(BaseModel):
    enabled: bool = True
    backend: str = "feedforward"
    lookback: int = 30
    blend_weight: float = 0.15
    hidden_layers: list[int] = Field(default_factory=lambda: [64, 32])
    max_iter: int = 200


class MetricsConfig(BaseModel):
    backtest_window: int = 200
    min_backtest_draws: int = 50
    random_trials: int = 500


class GamePredictionConfig(BaseModel):
    game: str
    enabled_strategies: list[str] = Field(default_factory=list)
    enabled_agents: list[str] = Field(default_factory=list)
    ensemble: EnsembleConfig = Field(default_factory=EnsembleConfig)
    nn: NNConfig = Field(default_factory=NNConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    strategy_params: dict[str, dict[str, Any]] = Field(default_factory=dict)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=32)
def load_game_config(game: str) -> GamePredictionConfig:
    """Merge defaults.yaml with per-game YAML; validate game exists in GAME_CONFIGS."""
    game_key = game.lower().strip()
    if game_key not in GAME_CONFIGS:
        raise ValueError(f"Unknown game '{game}'. Supported: {sorted(GAME_CONFIGS.keys())}")

    defaults = _load_yaml(_CONFIG_DIR / "defaults.yaml")
    game_path = _GAMES_DIR / f"{game_key}.yaml"
    if not game_path.exists():
        raise FileNotFoundError(f"No prediction config for game '{game_key}' at {game_path}")

    game_data = _load_yaml(game_path)
    merged = _deep_merge(defaults, game_data)
    merged["game"] = game_key
    return GamePredictionConfig.model_validate(merged)


def game_rules_from_config(game: str) -> GameRules:
    """Build GameRules from central GAME_CONFIGS."""
    cfg = GAME_CONFIGS.get(game, {}) or {}
    return GameRules(
        game=game,
        primary_count=int(cfg.get("primary_count", 5)),
        primary_min=int(cfg.get("primary_min", 1)),
        primary_max=int(cfg.get("primary_max", 99)),
        primary_unique=bool(cfg.get("primary_unique", True)),
        bonus_count=int(cfg.get("bonus_count", 0) or 0),
        bonus_min=int(cfg.get("bonus_min", 1)),
        bonus_max=int(cfg.get("bonus_max", 99)),
    )


def list_configured_games() -> list[str]:
    return sorted(p.stem for p in _GAMES_DIR.glob("*.yaml"))


def config_dir() -> str:
    return str(_CONFIG_DIR)