"""
Serafis Recommendation Algorithm — V1.2 Blended Scoring

Single entry point for the algorithm package:
- models/: RecommendationConfig, ScoredEpisode, Episode
- stages/: candidate_pool (Stage A), ranking (Stage B), orchestrator
- embedding/: get_embed_text, version and model constants
"""

# Ensure algorithm directory and its parent are on sys.path when loaded by algorithm_loader.
# Parent allows server (e.g. schema) to do: from algorithm.models.episode import Episode
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

_algo_dir = Path(__file__).resolve().parent
_parent = _algo_dir.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))
if str(_algo_dir) not in sys.path:
    sys.path.insert(0, str(_algo_dir))

from models.config import RecommendationConfig, DEFAULT_CONFIG, resolve_config
from models.engagement import ensure_engagements
from models.episode import ensure_list, ensure_episode_by_content_id
from models.scoring import ScoredEpisode
from stages.candidate_pool import get_candidate_pool
from stages.ranking import rank_candidates, get_badges
from stages.ranking.user_vector import get_user_vector_mean
from stages.orchestrator import create_recommendation_queue
from embedding.embedding_strategy import (
    get_embed_text,
    STRATEGY_VERSION,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)


def get_candidate_pool_ids(
    excluded_ids: Set[str],
    episodes: List[Dict],
    config: Optional[RecommendationConfig] = None,
) -> List[str]:
    """
    Return episode ids for the candidate pool (Stage A only).
    Used by the server to know which embedding ids to fetch when using Pinecone.
    Accepts episodes as list of dicts (same as create_recommendation_queue).
    """
    config = resolve_config(config)
    episodes_typed = ensure_list(episodes)
    candidates = get_candidate_pool(excluded_ids, episodes_typed, config)
    return [ep.id or ep.content_id for ep in candidates if (ep.id or ep.content_id)]


__all__ = [
    "RecommendationConfig",
    "DEFAULT_CONFIG",
    "get_candidate_pool",
    "get_candidate_pool_ids",
    "rank_candidates",
    "create_recommendation_queue",
    "get_user_vector_mean",
    "ensure_episode_by_content_id",
    "ensure_engagements",
    "ScoredEpisode",
    "get_badges",
    "get_embed_text",
    "STRATEGY_VERSION",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
]
