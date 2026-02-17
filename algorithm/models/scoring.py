"""
Scoring model — ScoredEpisode and score/time helpers used by the pipeline.

Contains:
- ScoredEpisode: an episode with its recommendation scores
- days_since, recency_score, quality_score: used by candidate_pool and semantic_scoring
"""

import math
from datetime import datetime, timezone

from pydantic import BaseModel

from .episode import Episode


def days_since(date_str: str) -> int:
    """Days since a given ISO date string (for freshness and recency)."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 999


def recency_score(days_old: int, lambda_val: float = 0.03) -> float:
    """Recency score with exponential decay (~23 day half-life at 0.03)."""
    return math.exp(-lambda_val * days_old)


def quality_score(
    credibility: int,
    insight: int,
    credibility_multiplier: float = 1.5,
    max_score: float = 10.0,
) -> float:
    """Normalized quality score (0–1) with credibility weighted higher."""
    raw_score = credibility * credibility_multiplier + insight
    return raw_score / max_score


class ScoredEpisode(BaseModel):
    """An episode with all its scoring components."""

    episode: Episode
    similarity_score: float
    quality_score: float
    recency_score: float
    final_score: float
