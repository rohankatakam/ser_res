"""
Main ranking orchestration: user vector, blended scoring, series diversity.

Unified path for all four user-state cases. Same candidate pool, blended scoring,
and series diversity for every case. Only the similarity source differs.
"""

import logging
from typing import Dict, List, Optional

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement
from models.episode import Episode
from models.scoring import ScoredEpisode

from .blended_scoring import build_scored_episode
from .series_diversity import select_top_k_with_series_penalty
from .user_vector import get_user_vector_mean

logger = logging.getLogger(__name__)


def _get_sim_score(
    ep_id: str,
    content_id: str,
    similarity_by_id: Optional[Dict[str, float]],
    user_vector: Optional[List[float]],
    embeddings: Dict[str, List[float]],
) -> float:
    """
    Resolve similarity score for one candidate.

    Central flow for the four user-state cases:
    - Case 1 (no engagements, no categories): similarity_by_id is None, user_vector is None → 0.5
    - Case 2 (engagements, no categories): similarity_by_id or embeddings, user_vector present → from query/fetch
    - Case 3 (no engagements, categories): similarity_by_id or embeddings, user_vector present → from query/fetch
    - Case 4 (engagements, categories): same as 2/3
    """
    if similarity_by_id is not None:
        sim = similarity_by_id.get(ep_id) or similarity_by_id.get(content_id)
        if sim is not None:
            return sim
        logger.warning(
            "[sim_fallback] SIMILARITY_MISSING_IN_QUERY_RESULTS ep_id=%s content_id=%s",
            ep_id, content_id,
        )
        return 0.5

    # No Pinecone query results (fetch path or Case 1)
    if user_vector is None:
        # Case 1: no engagements, no categories selected — no semantic signal
        return 0.5

    ep_embedding = embeddings.get(ep_id) or embeddings.get(content_id)
    if not (ep_embedding and user_vector):
        logger.warning(
            "[sim_fallback] SIMILARITY_FETCH_PATH_NO_PINECONE ep_id=%s content_id=%s",
            ep_id, content_id,
        )
        return 0.5

    # Fetch path with user_vector: would need cosine similarity here if we had embeddings
    # Today the fetch path does not compute similarity in core; session route uses query path when possible
    return 0.5


def rank_candidates(
    engagements: List[Engagement],
    candidates: List[Episode],
    embeddings: Dict[str, List[float]],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
    similarity_by_id: Optional[Dict[str, float]] = None,
) -> List[ScoredEpisode]:
    """
    Rank candidates with blended scoring and series diversity.

    Four user-state cases (all use same pipeline: blended scoring + series diversity):
    1. No engagements, no categories selected → user_vector=None, sim=0.5 for all
    2. Engagements, no categories → user_vector=mean(engagements), similarity from Pinecone
    3. No engagements, categories selected → user_vector=category_anchor, similarity from Pinecone
    4. Engagements, categories selected → user_vector=blend(engagement,category), similarity from Pinecone
    """
    # User vector: four cases handled in user_vector.get_user_vector_mean
    user_vector = get_user_vector_mean(
        engagements,
        embeddings,
        config,
        category_anchor_vector=category_anchor_vector,
    )

    # For each candidate: similarity (from Pinecone or 0.5), then blended score
    scored: List[ScoredEpisode] = []
    for ep in candidates:
        ep_id = ep.id
        content_id = ep.content_id or ""
        sim_score = _get_sim_score(
            ep_id, content_id, similarity_by_id, user_vector, embeddings
        )
        scored.append(build_scored_episode(ep, sim_score, config))

    # 3) Sort by final_score
    scored.sort(key=lambda x: x.final_score, reverse=True)

    # 4) Series diversity: in-processing selection (max N per series, no adjacent same series)
    scored = select_top_k_with_series_penalty(
        scored,
        k=len(scored),
        alpha=config.series_penalty_alpha,
        max_per_series=config.max_episodes_per_series,
    )

    return scored
