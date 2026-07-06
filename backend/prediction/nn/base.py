"""Neural network backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from prediction.core.types import Draw, GameRules


class NNBackend(ABC):
    """Time-series model: fit on history, predict next primary numbers."""

    @abstractmethod
    def fit(self, history: list[Draw], rules: GameRules) -> None:
        ...

    @abstractmethod
    def predict_scores(self, history: list[Draw], rules: GameRules) -> list[float]:
        """Return score vector over primary number universe."""
        ...

    @property
    @abstractmethod
    def is_fitted(self) -> bool:
        ...