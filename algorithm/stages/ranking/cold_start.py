"""
Cold-start category diversity for top-N recommendations.

When cold start and diversity are enabled, ensures a minimum number of
episodes per configured category in the top N results.
"""

from typing import Dict, List, Set

from models.config import RecommendationConfig
from models.scoring import ScoredEpisode


def apply_cold_start_category_diversity(
    scored: List[ScoredEpisode],
    config: RecommendationConfig,
    top_n: int = 10,
) -> List[ScoredEpisode]:
    """
    Apply category diversity to cold start: ensure min per category in top N.

    Buckets scored episodes by primary category; fills top_n by round-robin
    across target categories (min_per_category each), then fills remaining
    by final_score. Preserves relative order within selected vs rest.
    """
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
