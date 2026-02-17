"""
Serafis Recommendation Algorithm — V1.2 Blended Scoring

Modular pipeline:
- models/: RecommendationConfig, ScoredEpisode, RecommendationSession
- utils/: scores, similarity, episode helpers
- stages/: candidate_pool (Stage A), semantic_scoring (Stage B), queue
- embedding_strategy: get_embed_text, version and model constants
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
