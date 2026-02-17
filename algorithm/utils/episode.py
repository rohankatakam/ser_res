"""
Episode helpers — category and metadata extraction.
"""

from typing import Dict, Optional


def get_episode_primary_category(episode: Dict) -> Optional[str]:
    """Get the primary (first) major category for an episode."""
    categories = episode.get("categories", {})
    major_cats = categories.get("major", [])
    return major_cats[0] if major_cats else None
