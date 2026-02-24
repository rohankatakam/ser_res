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
from stages.candidate_pool import get_candidate_pool, _filter_eligible_candidates
from stages.ranking import rank_candidates


def _candidates_from_query_results(
    query_results: List[Tuple[str, float]],
    episode_by_content_id: Dict[str, Episode],
    excluded_ids: Set[str],
    config: RecommendationConfig,
) -> Tuple[List[Episode], Dict[str, float]]:
    """
    Derive candidates and similarity map from Pinecone query results.
    Applies quality, freshness, exclusion filters; returns (candidates, similarity_by_id).
    """
    similarity_by_id = {vid: score for vid, score in query_results}
    candidates = []
    for vid, _ in query_results:
        ep = episode_by_content_id.get(vid)
        if not ep:
            continue
        ep_typed = Episode.model_validate(ep) if isinstance(ep, dict) else ep
        filtered = _filter_eligible_candidates([ep_typed], excluded_ids, config)
        if filtered:
            candidates.append(filtered[0])
    return candidates[: config.candidate_pool_size], similarity_by_id


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
    config: RecommendationConfig,
    category_anchor_vector: Optional[List[float]] = None,
    similarity_by_id: Optional[Dict[str, float]] = None,
) -> List[ScoredEpisode]:
    """Stage B: Rank candidates by similarity and blended scoring."""
    return rank_candidates(
        engagements,
        candidates,
        embeddings,
        config,
        category_anchor_vector=category_anchor_vector,
        similarity_by_id=similarity_by_id,
    )


def create_recommendation_queue(
    engagements: List[Dict],
    excluded_ids: Set[str],
    episodes: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: Optional[RecommendationConfig] = None,
    category_anchor_vector: Optional[List[float]] = None,
    query_results: Optional[List[Tuple[str, float]]] = None,
) -> Tuple[List[ScoredEpisode], bool, int]:
    """
    Create a ranked recommendation queue (Stage A → Stage B).

    When query_results is provided (from Pinecone query), candidates are derived from
    query results and similarity comes from Pinecone scores (no candidate embedding fetch).

    Returns:
        queue: List of ScoredEpisode sorted by final_score
        cold_start: True if no engagements
        user_vector_episodes: Number of engagements used for user vector
    """
    # Resolve config (use defaults when None)
    config = resolve_config(config)

    # Normalize inputs to models (server passes dicts)
    episode_by_content_id_typed = ensure_episode_by_content_id(episode_by_content_id)
    engagements_typed = ensure_engagements(engagements)

    # Stage A: Retrieve candidates
    if query_results:
        candidates, similarity_by_id = _candidates_from_query_results(
            query_results, episode_by_content_id_typed, excluded_ids, config
        )
    else:
        episodes_typed = ensure_list(episodes)
        candidates = _retrieve_candidates(excluded_ids, episodes_typed, config)
        similarity_by_id = None

    # Session metadata for cold start and user-vector count
    cold_start, user_vector_episodes = _session_metadata(engagements_typed, config)

    # Stage B: Rank candidates (similarity + blended scoring)
    queue = _rank_candidates(
        engagements_typed,
        candidates,
        embeddings,
        config,
        category_anchor_vector=category_anchor_vector,
        similarity_by_id=similarity_by_id,
    )

    return queue, cold_start, user_vector_episodes
