"""
Algorithm configuration — Stage A, Stage B, and ranking parameters.

RecommendationConfig defaults are defined here. The server may pass a dict
(e.g. from algorithm/config.json if present); from_dict() merges it with these defaults.
"""

from typing import Dict, Optional

from pydantic import BaseModel, model_validator


class RecommendationConfig(BaseModel):
    """Configuration for the recommendation algorithm."""

    # -------------------------------------------------------------------------
    # Stage A: Candidate Pool Pre-Selection
    # -------------------------------------------------------------------------

    # Min credibility score (0-5 scale). Episodes below this are excluded.
    credibility_floor: int = 2

    # Min combined score: credibility + insight. Ensures substantive content.
    # E.g. 5 means (credibility + insight) >= 5.
    combined_floor: int = 5

    # Only episodes published within this many days are eligible. Older episodes excluded.
    # Retry logic may expand to 60 or 90 days if too few candidates pass filters.
    freshness_window_days: int = 90

    # Max number of candidates returned from Stage A. Used in both fetch and query paths.
    # For Pinecone query path: top_k = candidate_pool_size (with metadata filter).
    candidate_pool_size: int = 150

    # -------------------------------------------------------------------------
    # Stage B: Semantic Matching / User Vector
    # -------------------------------------------------------------------------

    # Max number of recent engagements (by timestamp) used to build the user vector.
    # Engagements beyond this are ignored for personalization.
    user_vector_limit: int = 10

    # -------------------------------------------------------------------------
    # Blended Scoring Weights (must sum to 1.0)
    # final_score = weight_similarity * sim + weight_quality * quality + weight_recency * recency
    # -------------------------------------------------------------------------

    # Weight for similarity to user vector. Higher = more personalized.
    weight_similarity: float = 0.55
    # Weight for content quality. Higher = more emphasis on credibility/insight.
    weight_quality: float = 0.30
    # Weight for recency. Higher = fresher content favored.
    weight_recency: float = 0.15

    # -------------------------------------------------------------------------
    # Quality Score (used for filtering, sorting, and blended score)
    # raw = credibility * credibility_multiplier + insight; normalized in scoring.py
    # -------------------------------------------------------------------------

    # Multiplier for credibility in quality formula. Higher = credibility weighs more vs insight.
    credibility_multiplier: float = 1.5

    # -------------------------------------------------------------------------
    # Recency Score
    # recency = exp(-recency_lambda * days_old). ~0.03 gives ~23 day half-life.
    # -------------------------------------------------------------------------

    recency_lambda: float = 0.03

    # -------------------------------------------------------------------------
    # Engagement Weights (for building user vector from engagement embeddings)
    # -------------------------------------------------------------------------

    # Weight for bookmark engagements vs click. Bookmark = stronger signal of preference.
    engagement_weight_bookmark: float = 2.0
    # Weight for click engagements when computing mean embedding.
    engagement_weight_click: float = 1.0

    # -------------------------------------------------------------------------
    # Category Anchor (when user has onboarding categories + engagements)
    # user_vector = (1 - α) * engagement_vector + α * category_anchor
    # -------------------------------------------------------------------------

    # Blend factor α. Higher = category preferences influence user vector more.
    category_anchor_weight: float = 0.15

    # -------------------------------------------------------------------------
    # Series Diversity (in-processing selection loop)
    # effective_score = final_score * (series_penalty_alpha ** series_count)
    # -------------------------------------------------------------------------

    # Hard cap: no more than this many episodes from the same series in the queue.
    max_episodes_per_series: int = 2
    # Penalty per additional episode from same series. 0.7 = 30% penalty per extra.
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
