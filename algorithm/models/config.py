"""
Algorithm configuration — Stage A, Stage B, and ranking parameters.

RecommendationConfig defaults are defined here. The server may pass a dict
(e.g. from algorithm/config.json if present); from_dict() merges it with these defaults.
"""

from typing import Dict, Optional

from pydantic import BaseModel, model_validator


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

    # Engagement type weights (bookmark and click only)
    engagement_weight_bookmark: float = 2.0
    engagement_weight_click: float = 1.0

    # Category anchor (blend when user set categories during onboarding)
    # (1-α)*engagement + α*category; α from category_anchor_weight
    category_anchor_weight: float = 0.15

    # Series diversity (in-processing selection loop)
    max_episodes_per_series: int = 2
    series_penalty_alpha: float = 0.7

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
            ew = config_dict["engagement_weights"]
            if "bookmark" in ew:
                flat["engagement_weight_bookmark"] = ew["bookmark"]
            if "click" in ew:
                flat["engagement_weight_click"] = ew["click"]
        if "category_anchor" in config_dict:
            ca = config_dict["category_anchor"]
            if "weight" in ca:
                flat["category_anchor_weight"] = ca["weight"]
        if "series_diversity" in config_dict:
            sd = config_dict["series_diversity"]
            flat["max_episodes_per_series"] = sd.get("max_per_series", 2)
            flat["series_penalty_alpha"] = sd.get("penalty_alpha", 0.7)
        allowed = set(cls.model_fields)
        filtered = {k: v for k, v in flat.items() if k in allowed}
        return cls.model_validate(filtered)


DEFAULT_CONFIG = RecommendationConfig()


def resolve_config(config: Optional["RecommendationConfig"]) -> "RecommendationConfig":
    """Return config or DEFAULT_CONFIG when none is provided."""
    return config if config is not None else DEFAULT_CONFIG
