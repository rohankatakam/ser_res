"""
Score-based badges for episodes (e.g. high_insight, high_credibility).

Used by the recommendation response to surface at most two badges per episode.
"""

from typing import List

from models.episode import Episode


def get_badges(ep: Episode) -> List[str]:
    """
    Score-based badges for an episode (max 2).

    Adds badges when insight, credibility, information, or entertainment
    scores are >= 3; returns up to two badges.
    """
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
