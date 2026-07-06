"""Tests for ensemble blending."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from prediction.config.loader import game_rules_from_config
from prediction.core.ensemble import build_ticket
from prediction.core.types import StrategyOutput


def test_blend_weights_sum_in_ticket():
    rules = game_rules_from_config("take5")
    outputs = [
        StrategyOutput(name="a", scores=[1.0] * 39, picks=[1, 2, 3, 4, 5]),
        StrategyOutput(name="b", scores=[0.5] * 39, picks=[6, 7, 8, 9, 10]),
    ]
    weights = {"a": 0.6, "b": 0.4}
    ticket = build_ticket("take5", outputs, weights, rules)
    assert len(ticket.primary) == 5
    assert all(1 <= n <= 39 for n in ticket.primary)
    assert abs(sum(ticket.weights_used.values()) - 1.0) < 0.01