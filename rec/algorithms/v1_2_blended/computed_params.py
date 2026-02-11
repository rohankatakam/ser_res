"""
Computed Parameters for v1_2_blended Algorithm

This module computes derived parameters from base parameters.
Computed parameters are readonly in the UI and are automatically
calculated when base parameters change.
"""

from typing import Dict, Any


def compute_parameters(base_params: Dict[str, Any], profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Compute derived parameters from base parameters.
    
    Args:
        base_params: User-tunable base parameters (from config.json)
        profile: Optional user profile with engagements for user vector computation
    
    Returns:
        Dictionary of computed parameter values
    """
    computed = {}
    
    # Extract base parameters with defaults
    stage_b = base_params.get("stage_b", {})
    engagement_weights = base_params.get("engagement_weights", {})
    
    # =========================================================================
    # Normalized Scoring Weights (must sum to 1.0 for algorithm)
    # =========================================================================
    weight_similarity = stage_b.get("weight_similarity", 0.85)
    weight_quality = stage_b.get("weight_quality", 0.10)
    weight_recency = stage_b.get("weight_recency", 0.05)
    
    weight_total = weight_similarity + weight_quality + weight_recency
    
    if weight_total > 0:
        computed["normalized_weight_similarity"] = weight_similarity / weight_total
        computed["normalized_weight_quality"] = weight_quality / weight_total
        computed["normalized_weight_recency"] = weight_recency / weight_total
    else:
        # Fallback if all weights are 0
        computed["normalized_weight_similarity"] = 0.33
        computed["normalized_weight_quality"] = 0.33
        computed["normalized_weight_recency"] = 0.34
    
    # =========================================================================
    # Recency Half-Life (derived from lambda)
    # =========================================================================
    recency_lambda = stage_b.get("recency_lambda", 0.03)
    if recency_lambda > 0:
        computed["recency_half_life_days"] = 0.693 / recency_lambda  # ln(2) / lambda
    else:
        computed["recency_half_life_days"] = float('inf')
    
    # =========================================================================
    # Quality Score Range (derived from credibility multiplier)
    # =========================================================================
    credibility_multiplier = stage_b.get("credibility_multiplier", 1.5)
    # Max credibility = 4, max insight = 4
    # Quality score = credibility * multiplier + insight
    computed["max_quality_score"] = 4 * credibility_multiplier + 4
    computed["min_quality_score"] = 1 * credibility_multiplier + 1
    
    # =========================================================================
    # Engagement Weight Normalization (relative proportions)
    # =========================================================================
    bookmark_weight = engagement_weights.get("bookmark", 10.0)
    listen_weight = engagement_weights.get("listen", 1.5)
    click_weight = engagement_weights.get("click", 1.0)
    
    engagement_total = bookmark_weight + listen_weight + click_weight
    
    if engagement_total > 0:
        computed["effective_bookmark_weight"] = bookmark_weight / engagement_total
        computed["effective_listen_weight"] = listen_weight / engagement_total
        computed["effective_click_weight"] = click_weight / engagement_total
        computed["bookmark_to_click_ratio"] = bookmark_weight / click_weight if click_weight > 0 else bookmark_weight
    else:
        computed["effective_bookmark_weight"] = 0.33
        computed["effective_listen_weight"] = 0.33
        computed["effective_click_weight"] = 0.34
        computed["bookmark_to_click_ratio"] = 1.0
    
    # =========================================================================
    # User Vector Computation (requires profile)
    # =========================================================================
    if profile:
        engagements = profile.get("engagements", [])
        user_vector_limit = stage_b.get("user_vector_limit", 10)
        
        computed["user_vector_size"] = min(len(engagements), user_vector_limit)
        computed["total_engagements"] = len(engagements)
        computed["vector_utilization"] = min(len(engagements) / user_vector_limit, 1.0) if user_vector_limit > 0 else 0
        
        # Compute weighted engagement distribution
        engagement_type_counts = {}
        for eng in engagements[-user_vector_limit:]:
            eng_type = eng.get("type", "click")
            engagement_type_counts[eng_type] = engagement_type_counts.get(eng_type, 0) + 1
        
        computed["vector_bookmark_count"] = engagement_type_counts.get("bookmark", 0)
        computed["vector_listen_count"] = engagement_type_counts.get("listen", 0)
        computed["vector_click_count"] = engagement_type_counts.get("click", 0)
    else:
        # No profile provided - set defaults
        computed["user_vector_size"] = 0
        computed["total_engagements"] = 0
        computed["vector_utilization"] = 0
        computed["vector_bookmark_count"] = 0
        computed["vector_listen_count"] = 0
        computed["vector_click_count"] = 0
    
    return computed
