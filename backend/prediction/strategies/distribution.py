"""Statistical distribution strategy: bias toward under-drawn numbers."""

from __future__ import annotations

from collections import Counter

import numpy as np

from prediction.core.registry import register_strategy
from prediction.core.types import Draw, GameRules, StrategyOutput
from prediction.strategies.base import BaseStrategy


@register_strategy("distribution")
class DistributionStrategy(BaseStrategy):
    """Favor numbers below expected frequency (mean-reversion bias)."""

    def analyze(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        if not history:
            uniform = [1.0 / size] * size
            return StrategyOutput(name=self.strategy_name, scores=uniform)

        counts = Counter()
        total_slots = 0
        for draw in history:
            for num in draw.primary:
                if rules.primary_min <= num <= rules.primary_max:
                    counts[num] += 1
                    total_slots += 1

        expected = total_slots / size if total_slots else 1.0
        scores: list[float] = []
        for offset in range(size):
            number = rules.primary_min + offset
            observed = float(counts.get(number, 0))
            # Higher score when observed is below expected (under-drawn)
            gap = max(0.0, expected - observed)
            scores.append(gap + 0.01)

        arr = np.asarray(scores, dtype=float)
        if arr.sum() > 0:
            arr = arr / arr.sum()

        ranked = sorted(
            range(rules.primary_min, rules.primary_max + 1),
            key=lambda n: arr[n - rules.primary_min],
            reverse=True,
        )
        picks: list[int] = []
        for number in ranked:
            if rules.primary_unique and number in picks:
                continue
            picks.append(number)
            if len(picks) >= rules.primary_count:
                break

        return StrategyOutput(
            name=self.strategy_name,
            scores=arr.tolist(),
            picks=picks,
            meta={"expected_per_number": round(expected, 3)},
        )