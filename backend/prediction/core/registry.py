"""Plugin registry for strategies and pattern agents."""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")

_STRATEGIES: dict[str, type] = {}
_AGENTS: dict[str, type] = {}


def register_strategy(name: str) -> Callable[[type], type]:
    """Decorator to register a strategy class by name."""

    def decorator(cls: type) -> type:
        _STRATEGIES[name] = cls
        cls.strategy_name = name  # type: ignore[attr-defined]
        return cls

    return decorator


def register_agent(name: str) -> Callable[[type], type]:
    """Decorator to register a pattern agent class by name."""

    def decorator(cls: type) -> type:
        _AGENTS[name] = cls
        cls.agent_name = name  # type: ignore[attr-defined]
        return cls

    return decorator


def get_strategy_class(name: str) -> type | None:
    return _STRATEGIES.get(name)


def get_agent_class(name: str) -> type | None:
    return _AGENTS.get(name)


def list_strategies() -> list[str]:
    return sorted(_STRATEGIES.keys())


def list_agents() -> list[str]:
    return sorted(_AGENTS.keys())


def ensure_plugins_loaded() -> None:
    """Import strategy and agent modules so decorators run."""
    from prediction.strategies import (  # noqa: F401
        delta,
        distribution,
        frequency,
        hot_cold,
    )
    from prediction.agents import (  # noqa: F401
        gaps,
        last_digit,
        repeats,
        sums,
    )