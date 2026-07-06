"""
Runtime timestamp helpers for experiment records.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict

_EPOCH_ID_SUFFIX = re.compile(r"-(\d{10,})$")


def runtime_timestamp_fields(now: datetime | None = None) -> Dict[str, int | str]:
    """Capture the current runtime instant in JS-friendly and ISO forms."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    epoch_seconds = current.timestamp()
    return {
        "timestamp": int(epoch_seconds * 1000),
        "timestamp_seconds": int(epoch_seconds),
        "timestamp_iso": current.isoformat(),
    }


def _seconds_from_raw_value(raw: float | int) -> float:
    value = float(raw)
    if value >= 1_000_000_000_000:
        return value / 1000.0
    return value


def _seconds_from_experiment_id(experiment_id: str) -> float | None:
    match = _EPOCH_ID_SUFFIX.search(str(experiment_id or ""))
    if not match:
        return None
    try:
        return _seconds_from_raw_value(int(match.group(1)))
    except (TypeError, ValueError):
        return None


def normalize_experiment_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure experiments expose runtime ISO time and millisecond timestamps."""
    if not isinstance(record, dict):
        return record

    normalized = dict(record)
    if normalized.get("timestamp_iso"):
        ts = normalized.get("timestamp")
        if isinstance(ts, (int, float)) and float(ts) < 1_000_000_000_000:
            normalized["timestamp"] = int(_seconds_from_raw_value(ts) * 1000)
        return normalized

    seconds: float | None = None
    ts = normalized.get("timestamp")
    if isinstance(ts, (int, float)):
        try:
            seconds = _seconds_from_raw_value(ts)
        except (TypeError, ValueError):
            seconds = None

    if seconds is None:
        seconds = _seconds_from_experiment_id(str(normalized.get("experiment_id") or ""))

    if seconds is None:
        return normalized

    normalized["timestamp"] = int(seconds * 1000)
    normalized["timestamp_iso"] = datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    return normalized