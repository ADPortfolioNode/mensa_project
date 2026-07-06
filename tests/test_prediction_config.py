"""Tests for prediction config loading."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from prediction.config.loader import game_rules_from_config, list_configured_games, load_game_config


def test_list_configured_games():
    games = list_configured_games()
    assert "take5" in games
    assert "pick3" in games
    assert "powerball" in games
    assert len(games) >= 5


def test_load_take5_config():
    cfg = load_game_config("take5")
    assert cfg.game == "take5"
    assert "frequency" in cfg.enabled_strategies
    assert cfg.ensemble.enabled is True
    assert sum(cfg.ensemble.initial_weights.values()) == pytest.approx(1.0, abs=0.05)


def test_game_rules_from_config():
    rules = game_rules_from_config("pick3")
    assert rules.primary_count == 3
    assert rules.primary_min == 0
    assert rules.primary_max == 9
    assert rules.primary_unique is False