"""Honest performance metrics — no inflated accuracy percentages."""

from __future__ import annotations

import random
from typing import Callable

import numpy as np

from prediction.core.types import Draw, GameRules, PredictionTicket


def _partial_hits(predicted: list[int], actual: list[int]) -> int:
    """Count matching primary numbers (order-independent)."""
    return len(set(predicted) & set(actual))


def _exact_match(predicted: list[int], actual: list[int]) -> bool:
    return sorted(predicted) == sorted(actual)


def random_ticket(rules: GameRules, rng: random.Random) -> list[int]:
    """Generate one random primary ticket respecting game rules."""
    pool = list(range(rules.primary_min, rules.primary_max + 1))
    if rules.primary_unique:
        return rng.sample(pool, min(rules.primary_count, len(pool)))
    return [rng.choice(pool) for _ in range(rules.primary_count)]


def score_prediction(
    ticket: PredictionTicket | list[int],
    actual: Draw,
    rules: GameRules,
) -> dict:
    """Score one prediction against an actual draw."""
    predicted = ticket.primary if isinstance(ticket, PredictionTicket) else ticket
    hits = _partial_hits(predicted, actual.primary)
    return {
        "partial_hits": hits,
        "partial_hit_rate": hits / max(rules.primary_count, 1),
        "exact_match": _exact_match(predicted, actual.primary),
        "sum_error": abs(sum(predicted) - sum(actual.primary)),
    }


def random_baseline_metrics(
    history: list[Draw],
    rules: GameRules,
    trials: int = 500,
    seed: int = 42,
) -> dict:
    """Compute expected performance of uniform random picks."""
    if len(history) < 2:
        return {"mean_partial_hits": 0.0, "exact_match_rate": 0.0, "trials": 0}

    rng = random.Random(seed)
    partial_hits: list[int] = []
    exact = 0
    eval_draws = history[-min(len(history) - 1, 100) :]

    for draw in eval_draws:
        for _ in range(max(1, trials // len(eval_draws))):
            ticket = random_ticket(rules, rng)
            partial_hits.append(_partial_hits(ticket, draw.primary))
            if _exact_match(ticket, draw.primary):
                exact += 1

    total = len(partial_hits) or 1
    return {
        "mean_partial_hits": round(sum(partial_hits) / total, 4),
        "exact_match_rate": round(exact / total, 6),
        "trials": total,
    }


def walk_forward_backtest(
    history: list[Draw],
    rules: GameRules,
    predict_fn: Callable[[list[Draw]], PredictionTicket | list[int]],
    window: int = 200,
    min_draws: int = 50,
) -> dict:
    """
    Walk-forward evaluation: predict draw t using history[:t], score vs draw[t].

    Returns honest metrics always shown alongside random baseline.
    """
    if len(history) < min_draws + 1:
        return {
            "status": "insufficient_data",
            "draws_available": len(history),
            "min_required": min_draws + 1,
        }

    start = max(1, len(history) - window)
    partial_hits: list[int] = []
    exact_matches = 0
    sum_errors: list[float] = []
    evaluated = 0

    for index in range(start, len(history)):
        train_hist = history[:index]
        actual = history[index]
        try:
            ticket = predict_fn(train_hist)
            predicted = ticket.primary if isinstance(ticket, PredictionTicket) else ticket
        except Exception:
            continue

        hits = _partial_hits(predicted, actual.primary)
        partial_hits.append(hits)
        if _exact_match(predicted, actual.primary):
            exact_matches += 1
        sum_errors.append(abs(sum(predicted) - sum(actual.primary)))
        evaluated += 1

    if evaluated == 0:
        return {"status": "no_evaluations", "evaluated": 0}

    mean_hits = float(np.mean(partial_hits))
    baseline = random_baseline_metrics(history[start:], rules)
    baseline_hits = baseline.get("mean_partial_hits", 0.0) or 0.001

    return {
        "status": "ok",
        "evaluated_draws": evaluated,
        "mean_partial_hits": round(mean_hits, 4),
        "exact_match_rate": round(exact_matches / evaluated, 6),
        "partial_hit_rate_at_1": round(sum(1 for h in partial_hits if h >= 1) / evaluated, 4),
        "partial_hit_rate_at_2": round(sum(1 for h in partial_hits if h >= 2) / evaluated, 4),
        "sum_mae": round(float(np.mean(sum_errors)), 4),
        "random_baseline": baseline,
        "lift_vs_random": round(mean_hits / baseline_hits, 4),
        "note": "Lottery exact-match rates are near zero; use mean_partial_hits and lift_vs_random.",
    }


def score_plugin_on_draw(
    plugin_picks: list[int],
    actual: Draw,
    rules: GameRules,
) -> float:
    """Partial hit rate for one plugin's picks vs actual draw (0.0–1.0)."""
    return _partial_hits(plugin_picks, actual.primary) / max(rules.primary_count, 1)