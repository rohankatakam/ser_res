"""Common Pydantic models shared across routes."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class SeriesInfo(BaseModel):
    id: str
    name: str


class EpisodeScores(BaseModel):
    insight: Optional[int] = None
    credibility: Optional[int] = None
    information: Optional[int] = None
    entertainment: Optional[int] = None


class EpisodeCard(BaseModel):
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    badges: List[str] = []
    key_insight: Optional[str] = None
    categories: Dict = {}
    similarity_score: Optional[float] = None
    quality_score: Optional[float] = None
    recency_score: Optional[float] = None
    final_score: Optional[float] = None
    queue_position: Optional[int] = None


class Engagement(BaseModel):
    episode_id: str
    type: str = "click"
    timestamp: Optional[str] = None
