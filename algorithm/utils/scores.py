"""
Score helpers — quality, recency, and time utilities used by both stages.
"""

import math
from datetime import datetime, timezone


def days_since(date_str: str) -> int:
    """Calculate days since a given ISO date string."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return 999


def recency_score(days_old: int, lambda_val: float = 0.03) -> float:
    """
    Recency score with exponential decay.
    lambda_val=0.03 gives ~23 day half-life.
    """
    return math.exp(-lambda_val * days_old)


def quality_score(
    credibility: int,
    insight: int,
    credibility_multiplier: float = 1.5,
    max_score: float = 10.0,
) -> float:
    """Normalized quality score with credibility weighted higher (0–1)."""
    raw_score = credibility * credibility_multiplier + insight
    return raw_score / max_score
