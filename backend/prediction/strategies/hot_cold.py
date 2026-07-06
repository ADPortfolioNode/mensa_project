"""Hot/cold strategy: blend recent (hot) and long-term (cold) frequency."""

from __future__ import annotations

from collections import Counter

from prediction.core.registry import register_strategy
from prediction.core.types import Draw, GameRules, StrategyOutput
from prediction.strategies.base import BaseStrategy


@register_strategy("hot_cold")
class HotColdStrategy(BaseStrategy):
    """Weight hot window heavily, cold window for overdue numbers."""

    def analyze(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        params = params or {}
        hot_window = int(params.get("hot_window", 20))
        cold_window = int(params.get("cold_window", 100))
        size = self._universe_size(rules)

        hot_hist = history[-hot_window:] if history else []
        cold_hist = history[-cold_window:] if history else []

        hot_counts = Counter()
        cold_counts = Counter()
        for draw in hot_hist:
            for num in draw.primary:
                hot_counts[num] += 1
        for draw in cold_hist:
            for num in draw.primary:
                cold_counts[num] += 1

        scores: list[float] = []
        for offset in range(size):
            number = rules.primary_min + offset
            hot = float(hot_counts.get(number, 0))
            cold = float(cold_counts.get(number, 0))
            # Hot numbers get 70% weight; cold under-represented get a boost
            cold_gap = max(0.0, (len(cold_hist) / max(rules.primary_count, 1)) - cold)
            scores.append((0.7 * hot) + (0.3 * cold_gap))

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
            name=self.strategy_name,
            scores=scores,
            picks=picks,
            meta={"hot_window": hot_window, "cold_window": cold_window},
        )