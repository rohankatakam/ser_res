"""Session-related Pydantic models."""

from typing import List, Optional

from pydantic import BaseModel

from .common import EpisodeCard, Engagement


class CreateSessionRequest(BaseModel):
    engagements: List[Engagement] = []
    excluded_ids: List[str] = []
    user_id: Optional[str] = None


class LoadMoreRequest(BaseModel):
    limit: int = 10  # DEFAULT_PAGE_SIZE


class EngageRequest(BaseModel):
    episode_id: str
    type: str = "click"
    user_id: Optional[str] = None
    episode_title: Optional[str] = None
    series_name: Optional[str] = None


class SessionDebugInfo(BaseModel):
    candidates_count: int
    user_vector_episodes: int
    embeddings_available: bool
    top_similarity_scores: List[float] = []
    top_quality_scores: List[float] = []
    top_final_scores: List[float] = []
    scoring_weights: dict = {}


class SessionResponse(BaseModel):
    session_id: str
    episodes: List[EpisodeCard]
    total_in_queue: int
    shown_count: int
    remaining_count: int
    algorithm: str
    debug: SessionDebugInfo | None = None
