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
) -> Optional[List[float]]:
    """
    Compute user activity vector using mean-pooling of engagement embeddings.

    Uses get_recent_engagement_embeddings; when weighted engagements are enabled,
    each embedding is scaled by engagement type weight and the mean is weighted.
    """
    pairs = get_recent_engagement_embeddings(
        engagements, embeddings, episode_by_content_id, config
    )
    if not pairs:
        return None
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
    if config.use_weighted_engagements:
        return list(sum(vectors) / sum(weights))
    return list(np.mean(vectors, axis=0))
