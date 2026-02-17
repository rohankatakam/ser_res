"""
Scoring model — a single episode with its recommendation scores.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoredEpisode:
    """An episode with all its scoring components."""
    episode: Dict
    similarity_score: float
    quality_score: float
    recency_score: float
    final_score: float
