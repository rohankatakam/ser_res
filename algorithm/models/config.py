"""
Algorithm configuration — Stage A, Stage B, and cold-start parameters.

Loaded from config.json and exposed as RecommendationConfig for the pipeline.
"""

from typing import Dict, List

from dataclasses import dataclass


@dataclass
class RecommendationConfig:
    """Configuration for the recommendation algorithm."""

    # Stage A: Candidate Pool Pre-Selection
    credibility_floor: int = 2
    combined_floor: int = 5
    freshness_window_days: int = 90
    candidate_pool_size: int = 150

    # Stage B: Semantic Matching
    user_vector_limit: int = 10

    # Scoring weights (must sum to 1.0)
    weight_similarity: float = 0.55
    weight_quality: float = 0.30
    weight_recency: float = 0.15

    # Quality scoring
    credibility_multiplier: float = 1.5
    max_quality_score: float = 10.0

    # Recency scoring
    recency_lambda: float = 0.03

    # Engagement type weights
    engagement_weights: Dict[str, float] = None
    use_weighted_engagements: bool = True

    # Sum-of-similarities mode (alternative to mean-pooling)
    use_sum_similarities: bool = False

    # Cold start category diversity
    cold_start_category_diversity_enabled: bool = False
    cold_start_category_min_per_category: int = 1
    cold_start_categories: List[str] = None

    # Cold start scoring weights
    cold_start_weight_quality: float = 0.60
    cold_start_weight_recency: float = 0.40

    def __post_init__(self):
        if self.engagement_weights is None:
            self.engagement_weights = {
                "bookmark": 2.0,
                "listen": 1.5,
                "click": 1.0,
            }
        total = self.weight_similarity + self.weight_quality + self.weight_recency
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "RecommendationConfig":
        """Create config from dictionary (e.g., loaded from JSON)."""
        flat = {}
        if "stage_a" in config_dict:
            flat.update(config_dict["stage_a"])
        if "stage_b" in config_dict:
            flat.update(config_dict["stage_b"])
        if "engagement_weights" in config_dict:
            flat["engagement_weights"] = config_dict["engagement_weights"]
        if "cold_start" in config_dict:
            cs = config_dict["cold_start"]
            if "weight_quality" in cs:
                flat["cold_start_weight_quality"] = cs["weight_quality"]
            if "weight_recency" in cs:
                flat["cold_start_weight_recency"] = cs["weight_recency"]
            if "category_diversity" in cs:
                cd = cs["category_diversity"]
                flat["cold_start_category_diversity_enabled"] = cd.get("enabled", False)
                flat["cold_start_category_min_per_category"] = cd.get("min_per_category", 1)
                flat["cold_start_categories"] = cd.get("categories", [])
        known_fields = {
            "credibility_floor", "combined_floor", "freshness_window_days",
            "candidate_pool_size", "user_vector_limit", "weight_similarity",
            "weight_quality", "weight_recency", "credibility_multiplier",
            "max_quality_score", "recency_lambda", "engagement_weights",
            "use_weighted_engagements", "use_sum_similarities",
            "cold_start_category_diversity_enabled", "cold_start_category_min_per_category",
            "cold_start_categories",
        }
        filtered = {k: v for k, v in flat.items() if k in known_fields}
        return cls(**filtered)


DEFAULT_CONFIG = RecommendationConfig()
