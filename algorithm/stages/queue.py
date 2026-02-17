"""
Queue orchestration — run Stage A then Stage B to produce the recommendation queue.
"""

from typing import Dict, List, Set, Tuple

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.scoring import ScoredEpisode
from stages.candidate_pool import get_candidate_pool
from stages.semantic_scoring import rank_candidates


def create_recommendation_queue(
    engagements: List[Dict],
    excluded_ids: Set[str],
    episodes: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: RecommendationConfig = None,
) -> Tuple[List[ScoredEpisode], bool, int]:
    """
    Create a ranked recommendation queue (Stage A → Stage B).

    Returns:
        queue: List of ScoredEpisode sorted by final_score
        cold_start: True if no engagements
        user_vector_episodes: Number of engagements used for user vector
    """
    if config is None:
        config = DEFAULT_CONFIG
    candidates = get_candidate_pool(excluded_ids, episodes, config)
    cold_start = not engagements
    user_vector_episodes = (
        min(len(engagements), config.user_vector_limit) if engagements else 0
    )
    queue = rank_candidates(
        engagements, candidates, embeddings, episode_by_content_id, config
    )
    return queue, cold_start, user_vector_episodes
