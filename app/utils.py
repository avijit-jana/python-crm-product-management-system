# app/utils.py
from typing import Any
from datetime import datetime


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def parse_date_iso(s: Any):
    """Return datetime or None for ISO-like strings; tolerant to None."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        try:
            # fallback for pandas Timestamp strings
            from dateutil import parser

            return parser.parse(str(s))
        except Exception:
            return None