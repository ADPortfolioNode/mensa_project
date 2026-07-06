"""Last-digit agent: cluster on historically common terminal digits."""

from __future__ import annotations

from collections import Counter

from prediction.agents.base import BaseAgent
from prediction.core.registry import register_agent
from prediction.core.types import Draw, GameRules, StrategyOutput


@register_agent("last_digit")
class LastDigitAgent(BaseAgent):
    """Favor numbers whose last digit matches recent hot terminal digits."""

    def score(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        digit_counts: Counter[int] = Counter()

        for draw in history:
            for num in draw.primary:
                digit_counts[num % 10] += 1

        hot_digits = {d for d, _ in digit_counts.most_common(3)} or set(range(10))
        scores: list[float] = []
        for offset in range(size):
            number = rules.primary_min + offset
            scores.append(float(digit_counts.get(number % 10, 0)) + (0.5 if (number % 10) in hot_digits else 0.0))

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
            meta={"hot_digits": sorted(hot_digits)},
        )