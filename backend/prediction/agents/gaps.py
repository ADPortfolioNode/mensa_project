"""Gaps agent: favor overdue numbers (longest since last appearance)."""

from __future__ import annotations

from prediction.agents.base import BaseAgent
from prediction.core.registry import register_agent
from prediction.core.types import Draw, GameRules, StrategyOutput


@register_agent("gaps")
class GapsAgent(BaseAgent):
    """Boost numbers with the largest gap since last seen."""

    def score(
        self,
        history: list[Draw],
        rules: GameRules,
        params: dict | None = None,
    ) -> StrategyOutput:
        size = self._universe_size(rules)
        last_seen = {rules.primary_min + i: len(history) for i in range(size)}

        for draw_index, draw in enumerate(history):
            for num in draw.primary:
                if rules.primary_min <= num <= rules.primary_max:
                    last_seen[num] = len(history) - 1 - draw_index

        scores = [float(last_seen.get(rules.primary_min + i, len(history))) for i in range(size)]
        ranked = sorted(
            range(rules.primary_min, rules.primary_max + 1),
            key=lambda n: last_seen.get(n, 0),
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
            meta={"max_gap": max(scores) if scores else 0},
        )