"""
Session model — a recommendation session with its queue and state.
"""

from typing import List, Set

from pydantic import BaseModel, Field

from .config import RecommendationConfig
from .scoring import ScoredEpisode


class RecommendationSession(BaseModel):
    """A recommendation session with pre-computed ranked queue."""

    session_id: str
    queue: List[ScoredEpisode]
    shown_indices: Set[int] = Field(default_factory=set)
    engaged_ids: Set[str] = Field(default_factory=set)
    excluded_ids: Set[str] = Field(default_factory=set)
    created_at: str
    cold_start: bool
    user_vector_episodes: int
    config: RecommendationConfig
