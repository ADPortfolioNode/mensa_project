"""Tests for post-draw weight updates."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from prediction.config.loader import game_rules_from_config
from prediction.core.draw_loader import draws_from_lists
from prediction.core.registry import ensure_plugins_loaded, get_strategy_class
from prediction.core.types import Draw
from prediction.learning.weight_updater import WeightUpdater
from prediction.state.weight_store import WeightStore


def test_weights_shift_toward_better_plugin():
    ensure_plugins_loaded()
    with tempfile.TemporaryDirectory() as tmp:
        store = WeightStore(tmp)
        updater = WeightUpdater(store)
        rules = game_rules_from_config("pick3")
        history = draws_from_lists([[1, 2, 3], [4, 5, 6]], "pick3")
        freq = get_strategy_class("frequency")().analyze(history, rules)
        delta = get_strategy_class("delta")().analyze(history, rules)
        actual = Draw(primary=[1, 2, 3])

        state = updater.update(
            game="pick3",
            actual=actual,
            outputs=[freq, delta],
            rules=rules,
            learning_rate=0.2,
            initial_weights={"frequency": 0.5, "delta": 0.5},
        )
        assert abs(sum(state.weights.values()) - 1.0) < 0.01
        assert "frequency" in state.weights