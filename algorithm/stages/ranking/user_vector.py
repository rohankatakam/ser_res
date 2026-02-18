"""
User vector computation (mean-pool of engagement embeddings).

Builds a single vector representing the user from their recent engagements,
optionally weighted by engagement type.
"""

from typing import Dict, List, Optional

import numpy as np

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement
from models.episode import Episode

from .engagement_embeddings import get_recent_engagement_embeddings


def get_user_vector_mean(
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
) -> Optional[List[float]]:
    """
    Compute user activity vector: mean-pool of engagement embeddings, optionally
    blended with category anchor (query hydration).

    - No engagements + category_anchor: return category_anchor (cold start).
    - Engagements + category_anchor: blend (1-α)*engagement_vector + α*category_anchor.
    - Engagements only / no category_anchor: return engagement mean (current behavior).
    - No engagements, no category_anchor: return None.
    """
    pairs = get_recent_engagement_embeddings(
        engagements, embeddings, episode_by_content_id, config
    )
    engagement_vector: Optional[List[float]] = None
    if pairs:
        vectors = []
        weights = []
        for eng, embedding in pairs:
            if config.use_weighted_engagements:
                w = config.engagement_weights.get(eng.type, 1.0)
                vectors.append(np.array(embedding) * w)
                weights.append(w)
            else:
                vectors.append(np.array(embedding))
                weights.append(1.0)
        engagement_vector = (
            list(sum(vectors) / sum(weights))
            if config.use_weighted_engagements
            else list(np.mean(vectors, axis=0))
        )

    use_anchor = (
        category_anchor_vector is not None
        and len(category_anchor_vector) > 0
        and getattr(config, "category_anchor_enabled", True)
    )

    if not engagement_vector:
        if use_anchor:
            return category_anchor_vector
        return None

    if not use_anchor:
        return engagement_vector

    # Blend: (1 - α) * engagement + α * category_anchor
    alpha = getattr(config, "category_anchor_weight", 0.15)
    alpha = max(0.0, min(1.0, alpha))
    eng_arr = np.array(engagement_vector)
    anc_arr = np.array(category_anchor_vector)
    if len(eng_arr) != len(anc_arr):
        return engagement_vector
    blended = (1.0 - alpha) * eng_arr + alpha * anc_arr
    norm = np.linalg.norm(blended)
    if norm > 1e-9:
        blended = blended / norm
    return list(blended)
