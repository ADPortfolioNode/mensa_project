"""Delta pattern strategy: favor numbers that follow recent step changes."""

from __future__ import annotations

from collections import Counter

from prediction.core.registry import register_strategy
from prediction.core.types import Draw, GameRules, StrategyOutput
from prediction.strategies.base import BaseStrategy


@register_strategy("delta")
class DeltaStrategy(BaseStrategy):
    """Predict based on consecutive-draw deltas between sorted primaries."""

    def analyze(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        delta_counts: Counter[int] = Counter()

        for index in range(1, len(history)):
            prev = sorted(history[index - 1].primary)
            curr = sorted(history[index].primary)
            length = min(len(prev), len(curr))
            for pos in range(length):
                delta_counts[curr[pos] - prev[pos]] += 1

        if not history:
            return StrategyOutput(name=self.strategy_name, scores=self._empty_scores(rules))

        last = sorted(history[-1].primary)
        predicted: list[int] = []
        common_deltas = [d for d, _ in delta_counts.most_common(3)]
        if not common_deltas:
            common_deltas = [0]

        for pos, base in enumerate(last[: rules.primary_count]):
            delta = common_deltas[pos % len(common_deltas)]
            candidate = int(base + delta)
            candidate = max(rules.primary_min, min(rules.primary_max, candidate))
            if rules.primary_unique and candidate in predicted:
                candidate = min(rules.primary_max, candidate + 1)
            predicted.append(candidate)

        while len(predicted) < rules.primary_count:
            predicted.append(rules.primary_min)

        scores = [0.0] * size
        for number in predicted:
            idx = number - rules.primary_min
            if 0 <= idx < size:
                scores[idx] += 1.0

        return StrategyOutput(
            name=self.strategy_name,
            scores=scores,
            picks=predicted[: rules.primary_count],
            meta={"delta_modes": dict(delta_counts.most_common(5))},
        )