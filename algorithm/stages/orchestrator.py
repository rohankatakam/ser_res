"""
Pipeline orchestrator — runs Stage A (candidate pool) then Stage B (ranking)
to produce the final recommendation queue.

The main entry point is create_recommendation_queue, which runs retrieval then ranking
and returns the queue plus session metadata (cold_start, user_vector_episodes).
"""

from typing import Dict, List, Optional, Set, Tuple

from models.config import RecommendationConfig, resolve_config
from models.engagement import Engagement, ensure_engagements
from models.episode import Episode, ensure_episode_by_content_id, ensure_list
from models.scoring import ScoredEpisode
from stages.candidate_pool import get_candidate_pool
from stages.ranking import rank_candidates


def _session_metadata(
    engagements: List[Engagement],
    config: RecommendationConfig,
) -> Tuple[bool, int]:
    """
    Compute session-level flags and counts.

    Returns:
        cold_start: True if the user has no engagements yet.
        user_vector_episodes: Number of engagements used for the user vector (capped by config).
    """
    cold_start = not engagements
    user_vector_episodes = (
        min(len(engagements), config.user_vector_limit) if engagements else 0
    )
    return cold_start, user_vector_episodes


def _retrieve_candidates(
    excluded_ids: Set[str],
    episodes: List[Episode],
    config: RecommendationConfig,
) -> List[Episode]:
    """Stage A: Retrieve candidate pool via quality and freshness filters."""
    return get_candidate_pool(excluded_ids, episodes, config)


def _rank_candidates(
    engagements: List[Engagement],
    candidates: List[Episode],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig,
) -> List[ScoredEpisode]:
    """Stage B: Rank candidates by similarity and blended scoring."""
    return rank_candidates(
        engagements, candidates, embeddings, episode_by_content_id, config
    )


def create_recommendation_queue(
    engagements: List[Dict],
    excluded_ids: Set[str],
    episodes: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: Optional[RecommendationConfig] = None,
) -> Tuple[List[ScoredEpisode], bool, int]:
    """
    Create a ranked recommendation queue (Stage A → Stage B).

    Returns:
        queue: List of ScoredEpisode sorted by final_score
        cold_start: True if no engagements
        user_vector_episodes: Number of engagements used for user vector
    """
    # Resolve config (use defaults when None)
    config = resolve_config(config)

    # Normalize inputs to models (server passes dicts)
    episodes_typed = ensure_list(episodes)
    episode_by_content_id_typed = ensure_episode_by_content_id(episode_by_content_id)
    engagements_typed = ensure_engagements(engagements)

    # Stage A: Retrieve candidates (quality + freshness filter)
    candidates = _retrieve_candidates(excluded_ids, episodes_typed, config)

    # Session metadata for cold start and user-vector count
    cold_start, user_vector_episodes = _session_metadata(engagements_typed, config)

    # Stage B: Rank candidates (similarity + blended scoring)
    queue = _rank_candidates(
        engagements_typed, candidates, embeddings, episode_by_content_id_typed, config
    )

    return queue, cold_start, user_vector_episodes
