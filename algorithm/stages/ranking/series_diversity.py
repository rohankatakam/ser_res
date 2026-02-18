"""
Series diversity — in-processing selection loop for max N per series and no adjacent same series.

Implements selection like X's Author Diversity Scorer: diversity is applied during
selection to avoid utility sacrifice from post-hoc reordering.
"""

from typing import Dict, List, Optional

from models.scoring import ScoredEpisode


def select_top_k_with_series_penalty(
    scored_list: List[ScoredEpisode],
    k: int = 10,
    alpha: float = 0.7,
    max_per_series: int = 2,
    no_adjacent_same_series: bool = True,
) -> List[ScoredEpisode]:
    """
    Select top-K from scored candidates with series diversity constraints.

    Uses an in-processing selection loop: for each slot, picks the best remaining
    candidate by effective_score = final_score * (alpha ** series_count[series_id]).
    If no_adjacent_same_series and the candidate's series equals the last selected
    series, effective_score is zeroed.

    Args:
        scored_list: Candidates sorted by final_score (desc). Not mutated.
        k: Number to select.
        alpha: Penalty factor per additional episode from same series (0 < alpha <= 1).
        max_per_series: Hard cap; candidates from series already at this count are skipped.
        no_adjacent_same_series: If True, disallow consecutive same-series picks.

    Returns:
        Ordered list of up to k ScoredEpisodes.
    """
    remaining = list(scored_list)
    selected: List[ScoredEpisode] = []
    series_count: Dict[str, int] = {}
    last_selected_series_id: Optional[str] = None

    for _ in range(min(k, len(remaining))):
        best_idx: int | None = None
        best_effective: float = -1.0

        for idx, scored in enumerate(remaining):
            ep = scored.episode
            series_id = ep.series.get("id") if ep.series else None
            current_count = series_count.get(series_id, 0)

            # Hard cap: skip if series already at max
            if current_count >= max_per_series:
                continue

            # No adjacent same series: skip if matches last
            if no_adjacent_same_series and last_selected_series_id is not None:
                if series_id == last_selected_series_id:
                    continue

            # effective_score = final_score * (alpha ** series_count[series_id])
            effective = scored.final_score * (alpha ** current_count)
            if effective > best_effective:
                best_effective = effective
                best_idx = idx

        if best_idx is None:
            # No valid candidate (e.g., all series at cap or all adjacent)
            break

        chosen = remaining.pop(best_idx)
        selected.append(chosen)
        sid = chosen.episode.series.get("id") if chosen.episode.series else None
        series_count[sid] = series_count.get(sid, 0) + 1
        last_selected_series_id = sid

    return selected
