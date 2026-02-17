"""
Serafis Recommendation Algorithm — V1.2 Blended Scoring

Single entry point for the algorithm package:
- models/: RecommendationConfig, ScoredEpisode, RecommendationSession
- utils/: scores, similarity, episode helpers
- stages/: candidate_pool (Stage A), semantic_scoring (Stage B), queue
- embedding/: get_embed_text, version and model constants
"""

# Ensure algorithm directory is on sys.path when loaded by algorithm_loader
import sys
from pathlib import Path

_algo_dir = Path(__file__).resolve().parent
if str(_algo_dir) not in sys.path:
    sys.path.insert(0, str(_algo_dir))

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.scoring import ScoredEpisode
from models.session import RecommendationSession
from stages.candidate_pool import get_candidate_pool
from stages.semantic_scoring import rank_candidates, get_badges
from stages.queue import create_recommendation_queue
from embedding.embedding_strategy import (
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
