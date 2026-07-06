"""Tests for honest metrics."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from prediction.config.loader import game_rules_from_config
from prediction.core.draw_loader import draws_from_lists
from prediction.core.types import PredictionTicket
from prediction.metrics.evaluator import random_baseline_metrics, walk_forward_backtest


def test_random_baseline_is_modest():
    rules = game_rules_from_config("take5")
    history = draws_from_lists(
        [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15], [16, 17, 18, 19, 20]] * 20,
        "take5",
    )
    baseline = random_baseline_metrics(history, rules, trials=200)
    assert baseline["mean_partial_hits"] < 2.0
    assert baseline["exact_match_rate"] < 0.01


def test_walk_forward_returns_lift():
    rules = game_rules_from_config("pick3")
    history = draws_from_lists([[i % 10, (i + 1) % 10, (i + 2) % 10] for i in range(80)], "pick3")

    def predict_fn(train_hist):
        last = train_hist[-1].primary
        return PredictionTicket(game="pick3", primary=last)

    result = walk_forward_backtest(history, rules, predict_fn, window=50, min_draws=30)
    assert result["status"] == "ok"
    assert "lift_vs_random" in result
    assert result["exact_match_rate"] < 0.5