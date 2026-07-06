"""Built-in prediction strategies."""

from prediction.strategies import delta, distribution, frequency, hot_cold

__all__ = ["frequency", "delta", "hot_cold", "distribution"]