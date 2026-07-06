"""Repeats agent: boost numbers seen in recent draws."""

from __future__ import annotations

from collections import Counter

from prediction.agents.base import BaseAgent
from prediction.core.registry import register_agent
from prediction.core.types import Draw, GameRules, StrategyOutput


@register_agent("repeats")
class RepeatsAgent(BaseAgent):
    """Favor numbers that appeared in the last N draws."""

    def score(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        params = params or {}
        window = int(params.get("window", 5))
        size = self._universe_size(rules)
        recent = history[-window:] if history else []

        counts = Counter()
        for draw in recent:
            for num in draw.primary:
                counts[num] += 1

        scores = [float(counts.get(rules.primary_min + i, 0)) for i in range(size)]
        picks = [n for n, _ in counts.most_common(rules.primary_count)]

        return StrategyOutput(
            name=self.agent_name,
            scores=scores,
            picks=picks,
            meta={"repeat_window": window},
        )