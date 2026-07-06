"""Frequency analysis strategy: rank numbers by historical appearance count."""

from __future__ import annotations

from collections import Counter

from prediction.core.registry import register_strategy
from prediction.core.types import Draw, GameRules, StrategyOutput
from prediction.strategies.base import BaseStrategy


@register_strategy("frequency")
class FrequencyStrategy(BaseStrategy):
    """Weight numbers by how often they appeared in history."""

    def analyze(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        counts = Counter()
        for draw in history:
            for num in draw.primary:
                if rules.primary_min <= num <= rules.primary_max:
                    counts[num] += 1

        scores = [float(counts.get(rules.primary_min + i, 0)) for i in range(size)]
        picks = sorted(
            range(rules.primary_min, rules.primary_max + 1),
            key=lambda n: counts.get(n, 0),
            reverse=True,
        )[: rules.primary_count]

        if not rules.primary_unique:
            picks = picks[: rules.primary_count]

        return StrategyOutput(
            name=self.strategy_name,
            scores=scores,
            picks=picks,
            meta={"total_draws": len(history)},
        )