"""
Pydantic Models for Serafis Recommendation API

Defines request/response models for the API endpoints.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel


# ============================================================================
# Episode Models
# ============================================================================

class SeriesInfo(BaseModel):
    id: str
    name: str


class EpisodeScores(BaseModel):
    insight: int
    credibility: int
    information: int
    entertainment: int


class EntityInfo(BaseModel):
    name: str
    relevance: int
    context: Optional[str] = None


class CriticalViews(BaseModel):
    non_consensus_level: Optional[str] = None
    has_critical_views: Optional[bool] = None
    new_ideas_summary: Optional[str] = None
    key_insights: Optional[str] = None


class EpisodeCard(BaseModel):
    """Compact episode representation for lists/cards."""
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    badges: List[str]
    key_insight: Optional[str]
    categories: Dict[str, List[str]]
    
    # Recommendation metadata
    similarity_score: Optional[float] = None
    quality_score: Optional[float] = None
    recency_score: Optional[float] = None
    final_score: Optional[float] = None
    queue_position: Optional[int] = None


class EpisodeDetail(BaseModel):
    """Full episode representation with all details."""
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    categories: Dict[str, List[str]]
    entities: List[EntityInfo]
    people: List[Dict]
    key_insight: Optional[str]
    critical_views: Optional[CriticalViews]
    search_relevance_score: Optional[float]
    aggregate_score: Optional[float]
    top_in_categories: List[str]


# ============================================================================
# Request Models
# ============================================================================

class Engagement(BaseModel):
    """A user engagement with an episode."""
    episode_id: str
    type: str = "click"  # click, bookmark, listen
    timestamp: str


class CreateSessionRequest(BaseModel):
    """Request to create a new recommendation session."""
    engagements: List[Engagement] = []
    excluded_ids: List[str] = []


class LoadMoreRequest(BaseModel):
    """Request to load more from an existing session."""
    limit: int = 10


class EngageRequest(BaseModel):
    """Request to record an engagement within a session."""
    episode_id: str
    type: str = "click"
    timestamp: Optional[str] = None


# ============================================================================
# Response Models
# ============================================================================

class SessionDebugInfo(BaseModel):
    """Debug information for a session."""
    candidates_count: int
    user_vector_episodes: int
    embeddings_available: bool
    top_similarity_scores: List[float] = []
    top_quality_scores: List[float] = []
    top_final_scores: List[float] = []
    scoring_weights: Dict[str, float] = {}


class SessionResponse(BaseModel):
    """Response for session-based recommendation endpoints."""
    session_id: str
    episodes: List[EpisodeCard]
    total_in_queue: int
    shown_count: int
    remaining_count: int
    cold_start: bool
    algorithm: str = "v1.2_blended"
    debug: Optional[SessionDebugInfo] = None


class LegacyForYouResponse(BaseModel):
    """Legacy response format for backwards compatibility."""
    section: str = "for_you"
    title: str
    subtitle: str
    algorithm: str
    cold_start: bool
    episodes: List[Dict]
    session_id: str
    total_in_queue: int
    remaining_count: int
    debug: Optional[Dict] = None
