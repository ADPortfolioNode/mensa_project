"""Sums agent: target draw sums near historical distribution mode."""

from __future__ import annotations

from collections import Counter

import numpy as np

from prediction.agents.base import BaseAgent
from prediction.core.registry import register_agent
from prediction.core.types import Draw, GameRules, StrategyOutput


@register_agent("sums")
class SumsAgent(BaseAgent):
    """Score numbers that help reach the most common historical sum range."""

    def score(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        if not history:
            return StrategyOutput(name=self.agent_name, scores=[0.0] * size)

        sums = [sum(draw.primary) for draw in history]
        target_sum = int(np.median(sums))
        per_pick = max(1, target_sum // max(rules.primary_count, 1))

        scores = [0.0] * size
        for offset in range(size):
            number = rules.primary_min + offset
            # Numbers near the per-slot target get higher scores
            distance = abs(number - per_pick)
            scores[offset] = 1.0 / (1.0 + distance)

        ranked = sorted(
            range(rules.primary_min, rules.primary_max + 1),
            key=lambda n: scores[n - rules.primary_min],
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
            name=self.agent_name,
            scores=scores,
            picks=picks,
            meta={"target_sum": target_sum, "sum_distribution": dict(Counter(sums).most_common(3))},
        )