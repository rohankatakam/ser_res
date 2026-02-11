"""
Serafis Recommendation Algorithm — V1.2 Blended Scoring

This algorithm implements a 2-stage recommendation pipeline:
- Stage A: Quality and freshness pre-filtering
- Stage B: Blended scoring (semantic similarity + quality + recency)

Key features:
- Quality score integrated into final ranking (not just gating)
- Credibility weighted 1.5x higher than insight
- Recency boost with exponential decay
- Engagement-type weighting (bookmarks 2x, listens 1.5x)
"""

from .recommendation_engine import (
    RecommendationConfig,
    DEFAULT_CONFIG,
    get_candidate_pool,
    rank_candidates,
    create_recommendation_queue,
    ScoredEpisode,
    RecommendationSession,
    get_badges,
)

from .embedding_strategy import (
    get_embed_text,
    STRATEGY_VERSION,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)

__all__ = [
    "RecommendationConfig",
    "DEFAULT_CONFIG",
    "get_candidate_pool",
    "rank_candidates",
    "create_recommendation_queue",
    "ScoredEpisode",
    "RecommendationSession",
    "get_badges",
    "get_embed_text",
    "STRATEGY_VERSION",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
]
