"""
Algorithm configuration — Stage A, Stage B, and cold-start parameters.

RecommendationConfig defaults are defined here. The server may pass a dict
(e.g. from algorithm/config.json if present); from_dict() merges it with these defaults.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class RecommendationConfig(BaseModel):
    """Configuration for the recommendation algorithm."""

    # Stage A: Candidate Pool Pre-Selection
    credibility_floor: int = 2
    combined_floor: int = 5
    freshness_window_days: int = 90
    candidate_pool_size: int = 150

    # Pinecone query (when using query path instead of fetch)
    pinecone_query_top_k: int = 250

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
    engagement_weights: Dict[str, float] = Field(
        default_factory=lambda: {"bookmark": 2.0, "listen": 1.5, "click": 1.0}
    )
    use_weighted_engagements: bool = True

    # Category anchor (query hydration for cold start + blend when user set categories)
    # When category_anchor_vector is provided: blend at α. When None/empty (no onboarding categories): no blend.
    category_anchor_weight: float = 0.15  # α in blend: (1-α)*engagement + α*category

    # Cold start category diversity
    cold_start_category_diversity_enabled: bool = False
    cold_start_category_min_per_category: int = 1
    cold_start_categories: List[str] = Field(default_factory=list)

    # Cold start scoring weights
    cold_start_weight_quality: float = 0.60
    cold_start_weight_recency: float = 0.40

    # Series diversity (in-processing selection loop)
    series_diversity_enabled: bool = True
    max_episodes_per_series: int = 2
    series_penalty_alpha: float = 0.7
    no_adjacent_same_series: bool = True

    @model_validator(mode="after")
    def weights_sum_to_one(self):
        total = self.weight_similarity + self.weight_quality + self.weight_recency
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
        return self

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
        if "category_anchor" in config_dict:
            ca = config_dict["category_anchor"]
            if "weight" in ca:
                flat["category_anchor_weight"] = ca["weight"]
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
        if "series_diversity" in config_dict:
            sd = config_dict["series_diversity"]
            flat["series_diversity_enabled"] = sd.get("enabled", True)
            flat["max_episodes_per_series"] = sd.get("max_per_series", 2)
            flat["series_penalty_alpha"] = sd.get("penalty_alpha", 0.7)
            flat["no_adjacent_same_series"] = sd.get("no_adjacent_same_series", True)
        allowed = set(cls.model_fields)
        filtered = {k: v for k, v in flat.items() if k in allowed}
        return cls.model_validate(filtered)


DEFAULT_CONFIG = RecommendationConfig()


def resolve_config(config: Optional["RecommendationConfig"]) -> "RecommendationConfig":
    """Return config or DEFAULT_CONFIG when none is provided."""
    return config if config is not None else DEFAULT_CONFIG
