"""Base class for lottery analysis strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from prediction.core.types import Draw, GameRules, StrategyOutput


class BaseStrategy(ABC):
    """Analyze draw history and return a score vector over the number universe."""

    strategy_name: str = "base"

    @abstractmethod
    def analyze(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        """Return scored picks for the next draw."""
        ...

    def _universe_size(self, rules: GameRules) -> int:
        return rules.primary_universe_size

    def _empty_scores(self, rules: GameRules) -> list[float]:
        return [0.0] * self._universe_size(rules)