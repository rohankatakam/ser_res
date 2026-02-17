"""
Stage B: Semantic Matching & Blended Scoring

User vector (mean-pool or sum-of-similarities), similarity scoring,
quality/recency blend, cold-start handling, and optional category diversity.
"""

from typing import Dict, List, Optional, Set

import numpy as np

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.episode import Episode
from models.scoring import ScoredEpisode, days_since, quality_score, recency_score


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    v1_arr = np.array(v1)
    v2_arr = np.array(v2)
    dot_product = np.dot(v1_arr, v2_arr)
    norm_product = np.linalg.norm(v1_arr) * np.linalg.norm(v2_arr)
    return float(dot_product / norm_product) if norm_product > 0 else 0.0


def get_user_vector_mean(
    engagements: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> Optional[List[float]]:
    """Compute user activity vector using mean-pooling of engagement embeddings."""
    if not engagements:
        return None
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.get("timestamp", ""),
        reverse=True,
    )[: config.user_vector_limit]
    vectors = []
    weights = []
    for eng in sorted_eng:
        ep_id = eng.get("episode_id")
        embedding = embeddings.get(ep_id)
        if not embedding and ep_id in episode_by_content_id:
            real_id = episode_by_content_id[ep_id].id
            embedding = embeddings.get(real_id)
        if embedding:
            if config.use_weighted_engagements:
                w = config.engagement_weights.get(eng.get("type", "click"), 1.0)
                vectors.append(np.array(embedding) * w)
                weights.append(w)
            else:
                vectors.append(np.array(embedding))
                weights.append(1.0)
    if not vectors:
        return None
    if config.use_weighted_engagements:
        return list(sum(vectors) / sum(weights))
    return list(np.mean(vectors, axis=0))


def compute_similarity_sum(
    candidate: Episode,
    engagements: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> float:
    """Similarity as sum (or weighted avg) of similarities to each engagement."""
    if not engagements:
        return 0.0
    candidate_embedding = embeddings.get(candidate.id)
    if not candidate_embedding:
        return 0.0
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.get("timestamp", ""),
        reverse=True,
    )[: config.user_vector_limit]
    total_sim = 0.0
    total_weight = 0.0
    for eng in sorted_eng:
        ep_id = eng.get("episode_id")
        eng_embedding = embeddings.get(ep_id)
        if not eng_embedding and ep_id in episode_by_content_id:
            real_id = episode_by_content_id[ep_id].id
            eng_embedding = embeddings.get(real_id)
        if eng_embedding:
            sim = cosine_similarity(candidate_embedding, eng_embedding)
            if config.use_weighted_engagements:
                w = config.engagement_weights.get(eng.get("type", "click"), 1.0)
                total_sim += sim * w
                total_weight += w
            else:
                total_sim += sim
                total_weight += 1.0
    return total_sim / total_weight if total_weight > 0 else 0.0


def apply_cold_start_category_diversity(
    scored: List[ScoredEpisode],
    config: RecommendationConfig,
    top_n: int = 10,
) -> List[ScoredEpisode]:
    """Apply category diversity to cold start: ensure min per category in top N."""
    if not config.cold_start_category_diversity_enabled or not config.cold_start_categories:
        return scored
    min_per_cat = config.cold_start_category_min_per_category
    target_categories = set(config.cold_start_categories)
    by_category: Dict[str, List[ScoredEpisode]] = {c: [] for c in target_categories}
    uncategorized: List[ScoredEpisode] = []
    for ep_scored in scored:
        cat = ep_scored.episode.get_primary_category()
        if cat and cat in by_category:
            by_category[cat].append(ep_scored)
        else:
            uncategorized.append(ep_scored)
    selected: List[ScoredEpisode] = []
    selected_ids: Set[str] = set()
    for _ in range(min_per_cat):
        for cat in target_categories:
            if by_category[cat]:
                ep = by_category[cat].pop(0)
                if ep.episode.id not in selected_ids:
                    selected.append(ep)
                    selected_ids.add(ep.episode.id)
                    if len(selected) >= top_n:
                        break
        if len(selected) >= top_n:
            break
    remaining = []
    for cat_list in by_category.values():
        remaining.extend(cat_list)
    remaining.extend(uncategorized)
    remaining.sort(key=lambda x: x.final_score, reverse=True)
    for ep in remaining:
        if ep.episode.id not in selected_ids:
            selected.append(ep)
            selected_ids.add(ep.episode.id)
            if len(selected) >= top_n:
                break
    selected.sort(key=lambda x: x.final_score, reverse=True)
    rest = [ep for ep in scored if ep.episode.id not in selected_ids]
    return selected + rest


def rank_candidates(
    engagements: List[Dict],
    candidates: List[Episode],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> List[ScoredEpisode]:
    """
    Rank candidates with blended scoring: w1*similarity + w2*quality + w3*recency.
    Cold start uses only quality + recency; optional category diversity applied.
    """
    user_vector = None
    if not config.use_sum_similarities:
        user_vector = get_user_vector_mean(
            engagements, embeddings, episode_by_content_id, config
        )
    cold_start = user_vector is None and not config.use_sum_similarities
    if config.use_sum_similarities:
        cold_start = not engagements

    scored = []
    for ep in candidates:
        ep_id = ep.id
        scores = ep.get_scores()

        if cold_start:
            sim_score = 0.5
        elif config.use_sum_similarities:
            sim_score = compute_similarity_sum(
                ep, engagements, embeddings, episode_by_content_id, config
            )
        else:
            ep_embedding = embeddings.get(ep_id)
            if ep_embedding and user_vector:
                sim_score = cosine_similarity(user_vector, ep_embedding)
            else:
                sim_score = 0.5

        qual_score = quality_score(
            scores.get("credibility") or 0,
            scores.get("insight") or 0,
            config.credibility_multiplier,
            config.max_quality_score,
        )
        age = days_since(ep.published_at or "")
        rec_score = recency_score(age, config.recency_lambda)

        if cold_start:
            final = (
                config.cold_start_weight_quality * qual_score
                + config.cold_start_weight_recency * rec_score
            )
        else:
            final = (
                config.weight_similarity * sim_score
                + config.weight_quality * qual_score
                + config.weight_recency * rec_score
            )
        scored.append(
            ScoredEpisode(
                episode=ep,
                similarity_score=sim_score,
                quality_score=qual_score,
                recency_score=rec_score,
                final_score=final,
            )
        )

    scored.sort(key=lambda x: x.final_score, reverse=True)
    if cold_start and config.cold_start_category_diversity_enabled:
        scored = apply_cold_start_category_diversity(scored, config, top_n=10)
    return scored


def get_badges(ep: Episode) -> List[str]:
    """Score-based badges for an episode (max 2)."""
    badges = []
    scores = ep.get_scores()
    if (scores.get("insight") or 0) >= 3:
        badges.append("high_insight")
    if (scores.get("credibility") or 0) >= 3:
        badges.append("high_credibility")
    if (scores.get("information") or 0) >= 3:
        badges.append("data_rich")
    if (scores.get("entertainment") or 0) >= 3:
        badges.append("engaging")
    return badges[:2]
