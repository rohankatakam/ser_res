"""
Session model — a recommendation session with its queue and state.
"""

from dataclasses import dataclass
from typing import List, Set

from .scoring import ScoredEpisode
from .config import RecommendationConfig


@dataclass
class RecommendationSession:
    """A recommendation session with pre-computed ranked queue."""
    session_id: str
    queue: List[ScoredEpisode]
    shown_indices: Set[int]
    engaged_ids: Set[str]
    excluded_ids: Set[str]
    created_at: str
    cold_start: bool
    user_vector_episodes: int
    config: RecommendationConfig
