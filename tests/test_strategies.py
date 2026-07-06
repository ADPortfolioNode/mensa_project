"""Tests for built-in strategies."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from prediction.config.loader import game_rules_from_config
from prediction.core.draw_loader import draws_from_lists
from prediction.core.registry import ensure_plugins_loaded, get_strategy_class


def _history(game: str, rows: list[list[int]]):
    return draws_from_lists(rows, game)


def test_frequency_strategy_take5():
    ensure_plugins_loaded()
    cls = get_strategy_class("frequency")
    rules = game_rules_from_config("take5")
    history = _history("take5", [[1, 2, 3, 4, 5], [1, 6, 7, 8, 9], [1, 10, 11, 12, 13]])
    output = cls().analyze(history, rules)
    assert output.name == "frequency"
    assert len(output.scores) == rules.primary_universe_size
    assert 1 in output.picks
    assert len(output.picks) == 5


def test_all_strategies_return_valid_picks():
    ensure_plugins_loaded()
    rules = game_rules_from_config("pick3")
    history = _history("pick3", [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    for name in ("frequency", "delta", "hot_cold", "distribution"):
        cls = get_strategy_class(name)
        output = cls().analyze(history, rules)
        assert len(output.picks) == 3
        for pick in output.picks:
            assert 0 <= pick <= 9