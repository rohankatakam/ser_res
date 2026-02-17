"""
Vector similarity and sum-of-similarities scoring.

Cosine similarity between vectors; similarity of a candidate to the user
as (weighted) average of similarities to each recent engagement embedding.
"""

from typing import Dict, List

import numpy as np

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement
from models.episode import Episode

from .engagement_embeddings import get_recent_engagement_embeddings


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    v1_arr = np.array(v1)
    v2_arr = np.array(v2)
    dot_product = np.dot(v1_arr, v2_arr)
    norm_product = np.linalg.norm(v1_arr) * np.linalg.norm(v2_arr)
    return float(dot_product / norm_product) if norm_product > 0 else 0.0


def compute_similarity_sum(
    candidate: Episode,
    engagements: List[Engagement],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> float:
    """
    Similarity as (weighted) average of cosine similarities to each engagement embedding.

    Uses get_recent_engagement_embeddings; candidate must have an embedding.
    """
    if not engagements:
        return 0.0
    candidate_embedding = embeddings.get(candidate.id)
    if not candidate_embedding:
        return 0.0
    pairs = get_recent_engagement_embeddings(
        engagements, embeddings, episode_by_content_id, config
    )
    total_sim = 0.0
    total_weight = 0.0
    for eng, eng_embedding in pairs:
        sim = cosine_similarity(candidate_embedding, eng_embedding)
        if config.use_weighted_engagements:
            w = config.engagement_weights.get(eng.type, 1.0)
            total_sim += sim * w
            total_weight += w
        else:
            total_sim += sim
            total_weight += 1.0
    return total_sim / total_weight if total_weight > 0 else 0.0
