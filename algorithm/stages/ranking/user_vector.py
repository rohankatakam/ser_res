"""
User vector computation — single source of truth for the four user-state cases.

Four cases (determined by engagements + category_anchor_vector):
  1. No engagements, no categories selected → None (quality + recency only)
  2. Engagements, no categories             → weighted mean of engagement embeddings
  3. No engagements, categories selected   → category_anchor (category interests drive)
  4. Engagements, categories selected      → blend(engagement, category_anchor)
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement

from .engagement_embeddings import get_recent_engagement_embeddings

logger = logging.getLogger(__name__)


def _engagement_weight(eng_type: str, config: RecommendationConfig) -> float:
    """Map engagement type to weight. Bookmark and click only; others default 1.0."""
    if eng_type == "bookmark":
        return config.engagement_weight_bookmark
    if eng_type == "click":
        return config.engagement_weight_click
    return 1.0


def _mean_pool_engagement_vectors(
    pairs: List[Tuple[Engagement, List[float]]],
    config: RecommendationConfig,
) -> List[float]:
    """Compute weighted mean of engagement embeddings (bookmark > click)."""
    if not pairs:
        return []
    vectors = []
    weights = []
    for eng, embedding in pairs:
        w = _engagement_weight(eng.type, config)
        vectors.append(np.array(embedding) * w)
        weights.append(w)
    return list(sum(vectors) / sum(weights))


def get_user_vector_mean(
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
) -> Optional[List[float]]:
    """
    Compute user vector for Pinecone query. Four cases flow naturally below.
    """
    has_categories = (
        category_anchor_vector is not None and len(category_anchor_vector) > 0
    )

    # Get engagement-derived vector (Cases 2 & 4)
    pairs = get_recent_engagement_embeddings(engagements, embeddings, config)
    pooled = _mean_pool_engagement_vectors(pairs, config)
    engagement_vector: Optional[List[float]] = list(pooled) if pooled else None

    # --- Case 1: No engagements, no categories → None ---
    if not engagement_vector and not has_categories:
        logger.info("[sim_fallback] USER_VECTOR_NONE_NO_ANCHOR no engagements, no category_anchor")
        return None

    # --- Case 3: No engagements, categories selected → category_anchor ---
    if not engagement_vector and has_categories:
        return category_anchor_vector

    # --- Case 2: Engagements, no categories → engagement vector only ---
    if not has_categories:
        return engagement_vector

    # --- Case 4: Engagements + categories → blend (1-α)*engagement + α*category ---
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
