"""
Stage B ranking: blend similarity, quality, and recency into a sorted queue.

Public API: rank_candidates.
- Submodules: user_vector, blended_scoring, series_diversity, engagement_embeddings.
"""

from .core import rank_candidates

__all__ = [
    "rank_candidates",
]
