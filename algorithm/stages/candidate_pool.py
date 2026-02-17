"""
Stage A: Candidate Pool Pre-Selection

Pre-selects candidates using quality gates and freshness.
Filters: credibility floor, combined quality floor, freshness window, exclusions.
Returns episodes sorted by quality score, capped at candidate_pool_size.

The public entry point is get_candidate_pool.
"""

from typing import List, Optional, Set

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.episode import Episode
from models.scoring import days_since, quality_score


def _passes_quality_gates(
    episode: Episode,
    config: RecommendationConfig,
) -> bool:
    """True if episode meets credibility and combined (credibility+insight) floors."""
    if episode.credibility < config.credibility_floor:
        return False
    if (episode.credibility + episode.insight) < config.combined_floor:
        return False
    return True


def _within_freshness_window(
    episode: Episode,
    config: RecommendationConfig,
) -> bool:
    """True if episode was published within the configured freshness window."""
    age = days_since(episode.published_at or "")
    return age <= config.freshness_window_days


def _not_excluded(episode: Episode, excluded_ids: Set[str]) -> bool:
    """True if episode id and content_id are not in the exclusion set."""
    content_id = episode.content_id or ""
    if episode.id in excluded_ids or content_id in excluded_ids:
        return False
    return True


def _filter_eligible_candidates(
    episodes: List[Episode],
    excluded_ids: Set[str],
    config: RecommendationConfig,
) -> List[Episode]:
    """Return episodes that pass quality gates, freshness window, and exclusion check."""
    candidates = []
    for ep in episodes:
        if not _passes_quality_gates(ep, config):
            continue
        if not _within_freshness_window(ep, config):
            continue
        if not _not_excluded(ep, excluded_ids):
            continue
        candidates.append(ep)
    return candidates


def _freshness_expansion_config(
    candidates: List[Episode],
    config: RecommendationConfig,
) -> Optional[RecommendationConfig]:
    """
    If too few candidates, return a config with a larger freshness window for retry.
    Returns None if no expansion should be applied.
    """
    if len(candidates) >= config.candidate_pool_size // 2:
        return None
    if config.freshness_window_days < 60:
        return RecommendationConfig(
            **(config.model_dump() | {"freshness_window_days": 60})
        )
    if config.freshness_window_days < 90:
        return RecommendationConfig(
            **(config.model_dump() | {"freshness_window_days": 90})
        )
    return None


def _sort_by_quality_and_cap(
    candidates: List[Episode],
    config: RecommendationConfig,
) -> List[Episode]:
    """Sort candidates by quality score (descending) and return up to candidate_pool_size."""
    candidates.sort(
        key=lambda ep: quality_score(
            ep.credibility,
            ep.insight,
            config.credibility_multiplier,
        ),
        reverse=True,
    )
    return candidates[:config.candidate_pool_size]


def get_candidate_pool(
    excluded_ids: Set[str],
    episodes: List[Episode],
    config: RecommendationConfig = DEFAULT_CONFIG,
) -> List[Episode]:
    """
    Stage A: Pre-select candidate pool using quality gates and freshness.

    Filters: credibility >= floor, (credibility+insight) >= combined floor,
    published within freshness window, not in excluded_ids.
    Returns episodes sorted by quality score (credibility weighted higher).
    """
    # Filter: quality gates, freshness window, exclusions
    candidates = _filter_eligible_candidates(episodes, excluded_ids, config)

    # Optional: retry with larger freshness window if too few candidates
    expanded = _freshness_expansion_config(candidates, config)
    if expanded is not None:
        return get_candidate_pool(excluded_ids, episodes, expanded)

    # Sort by quality and cap at candidate_pool_size
    return _sort_by_quality_and_cap(candidates, config)
