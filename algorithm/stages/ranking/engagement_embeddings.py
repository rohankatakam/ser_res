"""
Recent engagement–embedding pairs for user vector computation.

Provides sorted, limited engagement embeddings for mean-pool user vector.
Looks up embeddings by episode_id (Firestore); skips engagements without embeddings.
"""

import logging
from typing import Dict, List, Tuple

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement

logger = logging.getLogger(__name__)


def get_recent_engagement_embeddings(
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> List[Tuple[Engagement, List[float]]]:
    """
    Return recent engagements with their embeddings, sorted by timestamp (newest first).

    Looks up embedding by episode_id (Firestore). Skips engagements with no embedding.
    Limited to user_vector_limit entries.
    """
    if not engagements:
        return []

    # --- 1. Sort by timestamp and limit to user_vector_limit ---
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.timestamp,
        reverse=True,
    )[: config.user_vector_limit]

    # --- 2. Look up embedding for each engagement by episode_id ---
    result: List[Tuple[Engagement, List[float]]] = []
    skipped = 0

    for eng in sorted_eng:
        embedding = embeddings.get(eng.episode_id)
        if embedding:
            result.append((eng, embedding))
        else:
            skipped += 1

    # --- 3. Log when engagements are skipped (missing embeddings) ---
    if skipped:
        logger.warning(
            "[sim_fallback] ENGAGEMENT_EMBEDDING_SKIPPED skipped=%s total_engagements=%s",
            skipped,
            len(sorted_eng),
        )

    return result
