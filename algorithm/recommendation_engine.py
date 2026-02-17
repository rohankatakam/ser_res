"""
Serafis Recommendation Engine — V1.2

Thin facade over the modular pipeline:
- Stage A: candidate_pool (quality + freshness pre-selection)
- Stage B: semantic_scoring (user vector, similarity, blended scoring)
- Queue: create_recommendation_queue (orchestration)

All implementation lives in models/, utils/, and stages/.
This module re-exports the public API for backward compatibility.
"""

# Ensure algorithm directory is on sys.path when loaded by algorithm_loader
import sys
from pathlib import Path

_algo_dir = Path(__file__).resolve().parent
if str(_algo_dir) not in sys.path:
    sys.path.insert(0, str(_algo_dir))

from models.config import RecommendationConfig, DEFAULT_CONFIG
from models.scoring import ScoredEpisode
from models.session import RecommendationSession
from stages.candidate_pool import get_candidate_pool
from stages.semantic_scoring import rank_candidates, get_badges
from stages.queue import create_recommendation_queue

__all__ = [
    "RecommendationConfig",
    "DEFAULT_CONFIG",
    "ScoredEpisode",
    "RecommendationSession",
    "get_candidate_pool",
    "rank_candidates",
    "create_recommendation_queue",
    "get_badges",
]
