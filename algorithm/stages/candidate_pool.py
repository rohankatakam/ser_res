"""
Stage A: Candidate Pool Pre-Selection

Pre-selects candidates using quality gates and freshness.
Filters: credibility floor, combined quality floor, freshness window, exclusions.
Returns episodes sorted by quality score, capped at candidate_pool_size.
"""

from typing import Dict, List, Set

from models.config import RecommendationConfig, DEFAULT_CONFIG
from utils.scores import days_since, quality_score


def get_candidate_pool(
    excluded_ids: Set[str],
    episodes: List[Dict],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> List[Dict]:
    """
    Stage A: Pre-select candidate pool using quality gates and freshness.

    Filters: credibility >= floor, (credibility+insight) >= combined floor,
    published within freshness window, not in excluded_ids.
    Returns episodes sorted by quality score (credibility weighted higher).
    """
    candidates = []

    for ep in episodes:
        ep_id = ep["id"]
        content_id = ep.get("content_id", "")
        scores = ep.get("scores", {})
        credibility = scores.get("credibility") or 0
        insight = scores.get("insight") or 0

        if credibility < config.credibility_floor:
            continue
        if (credibility + insight) < config.combined_floor:
            continue

        age = days_since(ep.get("published_at", ""))
        if age > config.freshness_window_days:
            continue

        if ep_id in excluded_ids or content_id in excluded_ids:
            continue

        candidates.append(ep)

    # Expand freshness if not enough candidates
    if len(candidates) < config.candidate_pool_size // 2:
        if config.freshness_window_days < 60:
            expanded = RecommendationConfig(
                **{**config.__dict__, "freshness_window_days": 60}
            )
            return get_candidate_pool(excluded_ids, episodes, expanded)
        if config.freshness_window_days < 90:
            expanded = RecommendationConfig(
                **{**config.__dict__, "freshness_window_days": 90}
            )
            return get_candidate_pool(excluded_ids, episodes, expanded)

    candidates.sort(
        key=lambda ep: quality_score(
            ep["scores"]["credibility"],
            ep["scores"]["insight"],
            config.credibility_multiplier,
        ),
        reverse=True,
    )
    return candidates[:config.candidate_pool_size]
