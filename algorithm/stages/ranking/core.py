"""
Main ranking orchestration: mean-pool user vector, then blended scoring.

Blends similarity, quality, and recency; applies optional cold-start category diversity.
Submodules used: user_vector, blended_scoring, cold_start.
"""

import logging
from typing import Dict, List, Optional

from models.config import RecommendationConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)
from models.engagement import Engagement
from models.episode import Episode
from models.scoring import ScoredEpisode

from .blended_scoring import build_scored_episode
from .cold_start import apply_cold_start_category_diversity
from .series_diversity import select_top_k_with_series_penalty
from .user_vector import get_user_vector_mean


def rank_candidates(
    engagements: List[Engagement],
    candidates: List[Episode],
    embeddings: Dict[str, List[float]],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
    similarity_by_id: Optional[Dict[str, float]] = None,
) -> List[ScoredEpisode]:
    """
    Rank candidates with blended scoring: w1*similarity + w2*quality + w3*recency.

    Cold start (no engagements, or no user vector): uses only quality + recency;
    optional category diversity applied to top 10. Otherwise, similarity is
    mean-pool user vector vs candidate embedding (from Pinecone query when available).
    """
    # 1) Compute user vector and detect cold start
    user_vector = get_user_vector_mean(
        engagements,
        embeddings,
        config,
        category_anchor_vector=category_anchor_vector,
    )
    cold_start = user_vector is None

    # 2) For each candidate: similarity, then blended score → ScoredEpisode
    scored: List[ScoredEpisode] = []
    for ep in candidates:
        ep_id = ep.id
        content_id = ep.content_id or ""
        # Prefer Pinecone query scores when provided (query path)
        if similarity_by_id is not None:
            sim_score = similarity_by_id.get(ep_id) or similarity_by_id.get(content_id)
            if sim_score is None:
                logger.warning(
                    "[sim_fallback] SIMILARITY_MISSING_IN_QUERY_RESULTS ep_id=%s content_id=%s",
                    ep_id, content_id,
                )
                sim_score = 0.5
        elif cold_start:
            sim_score = 0.5  # Cold start: no user vector; use neutral similarity
        else:
            # Fetch path: no Pinecone query results; use neutral score (all similarity from Pinecone)
            ep_embedding = embeddings.get(ep_id) or embeddings.get(content_id)
            if not (ep_embedding and user_vector):
                logger.warning(
                    "[sim_fallback] SIMILARITY_FETCH_PATH_NO_PINECONE ep_id=%s content_id=%s has_ep_emb=%s has_user_vec=%s",
                    ep_id, content_id, ep_embedding is not None, user_vector is not None,
                )
            sim_score = 0.5  # Fetch path: no Pinecone scores; use neutral
        scored.append(build_scored_episode(ep, sim_score, config, cold_start))

    # 3) Sort by final_score
    scored.sort(key=lambda x: x.final_score, reverse=True)

    # 4) If cold start and diversity enabled, apply category diversity to top 10
    if cold_start and config.cold_start_category_diversity_enabled:
        scored = apply_cold_start_category_diversity(scored, config, top_n=10)

    # 5) Series diversity: in-processing selection loop (max N per series, no adjacent same series)
    if config.series_diversity_enabled:
        scored = select_top_k_with_series_penalty(
            scored,
            k=len(scored),
            alpha=config.series_penalty_alpha,
            max_per_series=config.max_episodes_per_series,
            no_adjacent_same_series=config.no_adjacent_same_series,
        )
        # Debug: log top 10 series for verification (remove after validation)
        _log_series_diversity_debug(scored[:10])

    return scored


def _log_series_diversity_debug(top_scored):
    """Log top 10 series ids/names for debugging series diversity."""
    try:
        items = []
        for s in top_scored:
            ser = s.episode.series
            sid = ser.get("id") if ser else None
            sname = ser.get("name", "?") if ser else "?"
            items.append(f"{sname}({sid})")
        print(f"[series_diversity] top10 series: {items}", flush=True)
    except Exception:
        pass
