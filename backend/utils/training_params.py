"""
Shared training-parameter snapshots for score-linked recreation.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

TRAINING_PARAM_KEYS: tuple[str, ...] = (
    "target_accuracy",
    "training_target",
    "train_size",
    "validation_size",
    "n_estimators",
    "max_depth",
    "random_state",
    "window_size",
    "blend_step",
    "auto_tune",
    "max_iterations",
    "data_limit",
    "model_strategy",
    "blend_weight",
)


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_training_params(mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pull known training-parameter keys from a flat dict or nested training_params."""
    if not isinstance(mapping, dict):
        return {}

    nested = mapping.get("training_params")
    sources: list[dict] = [mapping]
    if isinstance(nested, dict):
        sources.insert(0, nested)

    params: Dict[str, Any] = {}
    for source in sources:
        for key in TRAINING_PARAM_KEYS:
            if key in source and source.get(key) is not None and key not in params:
                params[key] = source[key]

    if "max_iterations" not in params:
        fallback = mapping.get("max_train_attempts") or mapping.get("iterations")
        if fallback is not None:
            params["max_iterations"] = fallback

    return params


def snapshot_from_trainer(
    trainer: Any,
    *,
    train_size: Optional[float] = None,
    validation_size: Optional[float] = None,
    target_accuracy: Optional[float] = None,
    training_target: Optional[float] = None,
    model_strategy: Optional[str] = None,
    blend_weight: Optional[float] = None,
) -> Dict[str, Any]:
    """Capture the trainer knobs used for a scored run."""
    data_limit = getattr(trainer, "data_limit", None)
    return {
        "target_accuracy": _coerce_float(
            target_accuracy if target_accuracy is not None else getattr(trainer, "target_accuracy", None)
        ),
        "training_target": _coerce_float(training_target),
        "train_size": _coerce_float(
            train_size if train_size is not None else getattr(trainer, "train_size", None)
        ),
        "validation_size": _coerce_float(validation_size),
        "n_estimators": _coerce_int(getattr(trainer, "n_estimators", None)),
        "max_depth": _coerce_int(getattr(trainer, "max_depth", None)),
        "random_state": _coerce_int(getattr(trainer, "random_state", None)),
        "window_size": _coerce_int(getattr(trainer, "window_size", None)),
        "blend_step": _coerce_float(getattr(trainer, "blend_step", None)),
        "auto_tune": bool(getattr(trainer, "auto_tune", False)),
        "max_iterations": _coerce_int(getattr(trainer, "max_train_attempts", None)),
        "data_limit": _coerce_int(data_limit) if data_limit else None,
        "model_strategy": model_strategy,
        "blend_weight": _coerce_float(blend_weight),
    }


def normalize_leaderboard_entry(item: Dict[str, Any], *, default_timestamp: float = 0.0) -> Optional[Dict[str, Any]]:
    """Normalize a score row so it always carries recreation parameters."""
    if not isinstance(item, dict):
        return None

    accuracy = _coerce_float(item.get("accuracy"))
    if accuracy is None:
        return None

    entry: Dict[str, Any] = {
        "accuracy": float(accuracy),
        "timestamp": float(item.get("timestamp") or default_timestamp),
        "source": item.get("source"),
        "training_params": extract_training_params(item),
    }
    for key, value in entry["training_params"].items():
        entry[key] = value
    return entry


def merge_training_params(*mappings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for mapping in mappings:
        for key, value in extract_training_params(mapping or {}).items():
            if value is not None:
                merged[key] = value
    return merged


def params_to_defaults(params: Dict[str, Any]) -> Dict[str, Any]:
    """Map stored recreation params to train_settings / configure_training keys."""
    if not params:
        return {}
    return {
        key: params.get(key)
        for key in TRAINING_PARAM_KEYS
        if params.get(key) is not None
    }


def top_scored_params(leaderboard: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Return training params from the highest-accuracy leaderboard row."""
    rows = [normalize_leaderboard_entry(item) for item in (leaderboard or [])]
    rows = [row for row in rows if row]
    if not rows:
        return {}
    rows.sort(
        key=lambda row: (
            float(row.get("accuracy") or -1.0),
            float(row.get("timestamp") or 0.0),
        ),
        reverse=True,
    )
    return dict(rows[0].get("training_params") or {})