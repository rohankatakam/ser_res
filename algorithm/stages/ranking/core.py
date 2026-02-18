"""
Main ranking orchestration: user vector or sum-of-similarities, then blended scoring.

Blends similarity, quality, and recency; applies optional cold-start category diversity.
Submodules used: user_vector, similarity, blended_scoring, cold_start.
"""

from typing import Dict, List, Optional

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.engagement import Engagement
from models.episode import Episode
from models.scoring import ScoredEpisode

from .blended_scoring import build_scored_episode
from .cold_start import apply_cold_start_category_diversity
from .series_diversity import select_top_k_with_series_penalty
from .similarity import cosine_similarity, compute_similarity_sum
from .user_vector import get_user_vector_mean


def rank_candidates(
    engagements: List[Engagement],
    candidates: List[Episode],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
    category_anchor_vector: Optional[List[float]] = None,
) -> List[ScoredEpisode]:
    """
    Rank candidates with blended scoring: w1*similarity + w2*quality + w3*recency.

    Cold start (no engagements, or no user vector when not using sum_similarities):
    uses only quality + recency; optional category diversity applied to top 10.
    Similarity: either mean-pool user vector vs candidate embedding, or
    sum-of-similarities to each engagement embedding, per config.
    """
    # 1) Decide user representation and cold-start
    user_vector = None
    if not config.use_sum_similarities:
        user_vector = get_user_vector_mean(
            engagements,
            embeddings,
            episode_by_content_id,
            config,
            category_anchor_vector=category_anchor_vector,
        )
    cold_start = user_vector is None and not config.use_sum_similarities
    if config.use_sum_similarities:
        cold_start = not engagements

    # 2) For each candidate: similarity, then blended score → ScoredEpisode
    scored: List[ScoredEpisode] = []
    for ep in candidates:
        ep_id = ep.id
        if cold_start:
            sim_score = 0.5  # Cold start: no user vector; use neutral similarity
        elif config.use_sum_similarities:
            sim_score = compute_similarity_sum(
                ep, engagements, embeddings, episode_by_content_id, config
            )
        else:
            ep_embedding = embeddings.get(ep_id)
            if ep_embedding and user_vector:
                sim_score = cosine_similarity(user_vector, ep_embedding)
            else:
                sim_score = 0.5  # Missing embedding or user vector; neutral
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
