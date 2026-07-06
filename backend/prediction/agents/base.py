"""Base class for pattern-specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from prediction.core.types import Draw, GameRules, StrategyOutput


class BaseAgent(ABC):
    """Analyze one pattern type (repeats, gaps, etc.) and return scores."""

    agent_name: str = "base"

    @abstractmethod
    def score(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        """Return score vector aligned with strategy output format."""
        ...

    def _universe_size(self, rules: GameRules) -> int:
        return rules.primary_universe_size