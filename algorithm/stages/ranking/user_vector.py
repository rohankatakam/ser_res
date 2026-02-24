"""
User vector computation (mean-pool of engagement embeddings).

Builds a single vector representing the user from their recent engagements,
optionally weighted by engagement type.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement

from .engagement_embeddings import get_recent_engagement_embeddings

logger = logging.getLogger(__name__)


def _mean_pool_engagement_vectors(
    pairs: List[Tuple[Engagement, List[float]]],
    config: RecommendationConfig,
) -> List[float]:
    """
    Compute weighted mean of engagement embeddings.

    Optionally weighted by engagement type (bookmark > listen > click per
    config.engagement_weights); produces a single vector for Pinecone query.
    """
    if not pairs:
        return []
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
    return (
        list(sum(vectors) / sum(weights))
        if config.use_weighted_engagements
        else list(np.mean(vectors, axis=0))
    )


def get_user_vector_mean(
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
) -> Optional[List[float]]:
    """
    Compute user activity vector: mean-pool of engagement embeddings, optionally
    blended with category anchor (query hydration).

    Category anchor is always used when provided (user set categories in onboarding).
    When None/empty (user didn't set categories): no blend, alpha=0.

    - No engagements + category_anchor: return category_anchor (cold start).
    - Engagements + category_anchor: blend (1-α)*engagement + α*category_anchor.
    - Engagements only / no category_anchor: return engagement mean.
    - No engagements, no category_anchor: return None.
    """
    # --- 1. Get recent engagement embeddings ---
    pairs = get_recent_engagement_embeddings(engagements, embeddings, config)
    # --- 2. Compute mean-pool engagement vector ---
    pooled = _mean_pool_engagement_vectors(pairs, config)
    engagement_vector: Optional[List[float]] = list(pooled) if pooled else None

    # --- 3. Category anchor: always used when provided ---
    # If user set categories in onboarding, category_anchor_vector is present; else None/empty → alpha=0.
    has_anchor = (
        category_anchor_vector is not None and len(category_anchor_vector) > 0
    )

    # --- 4. Handle no-engagement cases (cold start) ---
    if not engagement_vector:
        if has_anchor:
            return category_anchor_vector
        logger.info("[sim_fallback] USER_VECTOR_NONE_NO_ANCHOR no engagements, no category_anchor")
        return None

    # --- 5. No anchor (user didn't set categories): return plain engagement vector ---
    if not has_anchor:
        return engagement_vector

    # --- 6. Blend engagement vector with category anchor ---
    # (1 - α) * engagement + α * category_anchor; α from config (default 0.15). L2-normalize.
    alpha = max(0.0, min(1.0, config.category_anchor_weight))
    eng_arr = np.array(engagement_vector)
    anc_arr = np.array(category_anchor_vector)
    if len(eng_arr) != len(anc_arr):
        logger.warning(
            "[sim_fallback] USER_VECTOR_DIM_MISMATCH eng_len=%s anc_len=%s, returning engagement_vector",
            len(eng_arr), len(anc_arr),
        )
        return engagement_vector
    blended = (1.0 - alpha) * eng_arr + alpha * anc_arr
    norm = np.linalg.norm(blended)
    if norm > 1e-9:
        blended = blended / norm
    return list(blended)
