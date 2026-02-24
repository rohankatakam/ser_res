"""
Stage B ranking: blend similarity, quality, and recency into a sorted queue.

Public API: rank_candidates, get_badges.
- core: main orchestration (rank_candidates).
- Submodules: user_vector, blended_scoring, cold_start, badges, engagement_embeddings.
"""

from .badges import get_badges
from .core import rank_candidates

__all__ = [
    "rank_candidates",
    "get_badges",
]
