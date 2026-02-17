"""
Recent engagement–embedding pairs for user vector and similarity scoring.

Single place that sorts engagements by timestamp, limits by config, and resolves
episode_id (or content_id) to embedding so callers avoid duplicated logic.
"""

from typing import Dict, List, Tuple

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement
from models.episode import Episode


def get_recent_engagement_embeddings(
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> List[Tuple[Engagement, List[float]]]:
    """
    Return recent engagements with their embeddings, sorted by timestamp (newest first).

    Resolves episode_id → embedding; if not found, tries content_id → Episode.id → embedding.
    Skips engagements with no embedding. Limited to user_vector_limit entries.
    """
    if not engagements:
        return []
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.timestamp,
        reverse=True,
    )[: config.user_vector_limit]
    result: List[Tuple[Engagement, List[float]]] = []
    for eng in sorted_eng:
        ep_id = eng.episode_id
        embedding = embeddings.get(ep_id)
        # Resolve content_id → internal id for embedding lookup (e.g. Firebase vs local ids)
        if not embedding and ep_id in episode_by_content_id:
            real_id = episode_by_content_id[ep_id].id
            embedding = embeddings.get(real_id)
        if embedding:
            result.append((eng, embedding))
    return result
