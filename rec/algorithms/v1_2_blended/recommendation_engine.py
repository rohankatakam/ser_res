"""
Serafis Recommendation Engine — V1.2

Implements the refined 2-stage recommendation algorithm with:
- Stage A: Quality and freshness pre-filtering
- Stage B: Blended scoring (semantic similarity + quality + recency)

Key improvements in V1.2:
- Quality score integrated into final ranking (not just gating)
- Credibility weighted 1.5x higher than insight
- Recency boost with exponential decay
- Optional sum-of-similarities for diverse interests

Note: This module is designed to work with the new versioned architecture.
It receives a DataCache instance rather than creating one internally.
"""

import math
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass


# ============================================================================
# Configuration — V1.2 Parameters
# ============================================================================

@dataclass
class RecommendationConfig:
    """Configuration for the recommendation algorithm."""
    
    # Stage A: Candidate Pool Pre-Selection
    credibility_floor: int = 2
    combined_floor: int = 5
    freshness_window_days: int = 90
    candidate_pool_size: int = 150
    
    # Stage B: Semantic Matching
    user_vector_limit: int = 10  # Increased from 5 to capture more interests
    
    # Scoring weights (must sum to 1.0)
    weight_similarity: float = 0.55
    weight_quality: float = 0.30
    weight_recency: float = 0.15
    
    # Quality scoring
    credibility_multiplier: float = 1.5  # Weight credibility higher
    max_quality_score: float = 10.0  # Max possible C*1.5 + I = 4*1.5 + 4 = 10
    
    # Recency scoring
    recency_lambda: float = 0.03  # ~23 day half-life
    
    # Engagement type weights (for weighted user vector)
    engagement_weights: Dict[str, float] = None
    use_weighted_engagements: bool = True
    
    # Sum-of-similarities mode (alternative to mean-pooling)
    use_sum_similarities: bool = False
    
    def __post_init__(self):
        if self.engagement_weights is None:
            self.engagement_weights = {
                "bookmark": 2.0,
                "listen": 1.5,
                "click": 1.0,
            }
        
        # Validate weights sum to 1.0
        total = self.weight_similarity + self.weight_quality + self.weight_recency
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> "RecommendationConfig":
        """Create config from dictionary (e.g., loaded from JSON)."""
        # Flatten nested config structure
        flat = {}
        
        # Handle stage_a params
        if "stage_a" in config_dict:
            flat.update(config_dict["stage_a"])
        
        # Handle stage_b params
        if "stage_b" in config_dict:
            flat.update(config_dict["stage_b"])
        
        # Handle engagement_weights
        if "engagement_weights" in config_dict:
            flat["engagement_weights"] = config_dict["engagement_weights"]
        
        # Only include known fields
        known_fields = {
            "credibility_floor", "combined_floor", "freshness_window_days",
            "candidate_pool_size", "user_vector_limit", "weight_similarity",
            "weight_quality", "weight_recency", "credibility_multiplier",
            "max_quality_score", "recency_lambda", "engagement_weights",
            "use_weighted_engagements", "use_sum_similarities"
        }
        
        filtered = {k: v for k, v in flat.items() if k in known_fields}
        return cls(**filtered)


# Default configuration
DEFAULT_CONFIG = RecommendationConfig()


# ============================================================================
# Helper Functions
# ============================================================================

def days_since(date_str: str) -> int:
    """Calculate days since a given ISO date string."""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except:
        return 999


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    
    v1 = np.array(v1)
    v2 = np.array(v2)
    
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    
    return float(dot_product / norm_product) if norm_product > 0 else 0.0


def recency_score(days_old: int, lambda_val: float = 0.03) -> float:
    """
    Compute recency score with exponential decay.
    
    Args:
        days_old: Age of content in days
        lambda_val: Decay rate (0.03 gives ~23 day half-life)
    
    Returns:
        Score between 0 and 1, higher for fresher content
    """
    return math.exp(-lambda_val * days_old)


def quality_score(
    credibility: int,
    insight: int,
    credibility_multiplier: float = 1.5,
    max_score: float = 10.0
) -> float:
    """
    Compute normalized quality score with credibility weighted higher.
    
    Args:
        credibility: Credibility score (1-4)
        insight: Insight score (1-4)
        credibility_multiplier: How much more to weight credibility
        max_score: Maximum possible score for normalization
    
    Returns:
        Score between 0 and 1
    """
    raw_score = credibility * credibility_multiplier + insight
    return raw_score / max_score


# ============================================================================
# Stage A: Candidate Pool Pre-Selection
# ============================================================================

def get_candidate_pool(
    excluded_ids: Set[str],
    episodes: List[Dict],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> List[Dict]:
    """
    Stage A: Pre-select candidate pool using quality gates and freshness.
    
    Filters applied in order:
    1. Credibility >= floor
    2. Credibility + Insight >= combined floor
    3. Published within freshness window
    4. Not in excluded_ids
    
    Returns episodes sorted by quality score (with credibility weighted higher).
    
    Args:
        excluded_ids: Set of episode IDs to exclude
        episodes: List of episode dicts (from dataset)
        config: Algorithm configuration
    """
    candidates = []
    
    for ep in episodes:
        ep_id = ep["id"]
        content_id = ep.get("content_id", "")
        scores = ep.get("scores", {})
        credibility = scores.get("credibility") or 0
        insight = scores.get("insight") or 0
        
        # Gate 1: Credibility floor
        if credibility < config.credibility_floor:
            continue
        
        # Gate 2: Combined quality floor
        if (credibility + insight) < config.combined_floor:
            continue
        
        # Gate 3: Freshness
        age = days_since(ep.get("published_at", ""))
        if age > config.freshness_window_days:
            continue
        
        # Gate 4: Exclusions (check both ID and content_id)
        if ep_id in excluded_ids or content_id in excluded_ids:
            continue
        
        candidates.append(ep)
    
    # Expand freshness if not enough candidates
    if len(candidates) < config.candidate_pool_size // 2:
        if config.freshness_window_days < 60:
            expanded_config = RecommendationConfig(
                **{**config.__dict__, 'freshness_window_days': 60}
            )
            return get_candidate_pool(excluded_ids, episodes, expanded_config)
        elif config.freshness_window_days < 90:
            expanded_config = RecommendationConfig(
                **{**config.__dict__, 'freshness_window_days': 90}
            )
            return get_candidate_pool(excluded_ids, episodes, expanded_config)
    
    # Sort by quality score (with credibility weighted higher)
    candidates.sort(
        key=lambda ep: quality_score(
            ep["scores"]["credibility"],
            ep["scores"]["insight"],
            config.credibility_multiplier
        ),
        reverse=True
    )
    
    return candidates[:config.candidate_pool_size]


# ============================================================================
# Stage B: Semantic Matching & Blended Scoring
# ============================================================================

def get_user_vector_mean(
    engagements: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> Optional[List[float]]:
    """
    Compute user activity vector using mean-pooling.
    
    This is the simple approach: average the embeddings of recent engagements.
    
    Args:
        engagements: List of engagement dicts with episode_id and type
        embeddings: Dict mapping episode_id to embedding vector
        episode_by_content_id: Dict mapping content_id to episode dict
        config: Algorithm configuration
    """
    if not engagements:
        return None
    
    # Sort by timestamp, most recent first
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.get("timestamp", ""),
        reverse=True
    )[:config.user_vector_limit]
    
    vectors = []
    weights = []
    
    for eng in sorted_eng:
        ep_id = eng.get("episode_id")
        
        # Get embedding (try direct ID first, then content_id lookup)
        embedding = embeddings.get(ep_id)
        if not embedding and ep_id in episode_by_content_id:
            real_id = episode_by_content_id[ep_id]["id"]
            embedding = embeddings.get(real_id)
        
        if embedding:
            if config.use_weighted_engagements:
                eng_type = eng.get("type", "click")
                weight = config.engagement_weights.get(eng_type, 1.0)
                vectors.append(np.array(embedding) * weight)
                weights.append(weight)
            else:
                vectors.append(np.array(embedding))
                weights.append(1.0)
    
    if not vectors:
        return None
    
    if config.use_weighted_engagements:
        # Weighted mean
        weighted_sum = sum(vectors)
        return list(weighted_sum / sum(weights))
    else:
        # Simple mean
        return list(np.mean(vectors, axis=0))


def compute_similarity_sum(
    candidate: Dict,
    engagements: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> float:
    """
    Compute similarity using sum-of-similarities approach.
    
    This preserves interest diversity better than mean-pooling:
    - Compare candidate to EACH user engagement
    - Sum (or average) the similarities
    - Candidate that matches ANY interest gets credit
    """
    if not engagements:
        return 0.0
    
    candidate_embedding = embeddings.get(candidate["id"])
    if not candidate_embedding:
        return 0.0
    
    # Sort by timestamp, most recent first
    sorted_eng = sorted(
        engagements,
        key=lambda e: e.get("timestamp", ""),
        reverse=True
    )[:config.user_vector_limit]
    
    total_sim = 0.0
    total_weight = 0.0
    
    for eng in sorted_eng:
        ep_id = eng.get("episode_id")
        
        # Get embedding
        eng_embedding = embeddings.get(ep_id)
        if not eng_embedding and ep_id in episode_by_content_id:
            real_id = episode_by_content_id[ep_id]["id"]
            eng_embedding = embeddings.get(real_id)
        
        if eng_embedding:
            sim = cosine_similarity(candidate_embedding, eng_embedding)
            
            if config.use_weighted_engagements:
                eng_type = eng.get("type", "click")
                weight = config.engagement_weights.get(eng_type, 1.0)
                total_sim += sim * weight
                total_weight += weight
            else:
                total_sim += sim
                total_weight += 1.0
    
    return total_sim / total_weight if total_weight > 0 else 0.0


@dataclass
class ScoredEpisode:
    """An episode with all its scoring components."""
    episode: Dict
    similarity_score: float
    quality_score: float
    recency_score: float
    final_score: float


def rank_candidates(
    engagements: List[Dict],
    candidates: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> List[ScoredEpisode]:
    """
    Rank candidates using blended scoring.
    
    Final score = w1 * similarity + w2 * quality + w3 * recency
    
    Where:
    - similarity: Cosine similarity to user vector (or sum-of-similarities)
    - quality: Normalized quality score (credibility*1.5 + insight)
    - recency: Exponential decay based on days old
    
    Returns list of ScoredEpisode sorted by final_score descending.
    """
    # Compute user vector (for mean-pooling approach)
    user_vector = None
    if not config.use_sum_similarities:
        user_vector = get_user_vector_mean(
            engagements, embeddings, episode_by_content_id, config
        )
    
    cold_start = user_vector is None and not config.use_sum_similarities
    if config.use_sum_similarities:
        cold_start = not engagements
    
    scored = []
    
    for ep in candidates:
        ep_id = ep["id"]
        scores = ep.get("scores", {})
        
        # Compute similarity score
        if cold_start:
            # Cold start: no similarity, rely on quality + recency
            sim_score = 0.5  # Neutral
        elif config.use_sum_similarities:
            sim_score = compute_similarity_sum(
                ep, engagements, embeddings, episode_by_content_id, config
            )
        else:
            ep_embedding = embeddings.get(ep_id)
            if ep_embedding and user_vector:
                sim_score = cosine_similarity(user_vector, ep_embedding)
            else:
                sim_score = 0.5  # Neutral fallback
        
        # Compute quality score
        qual_score = quality_score(
            scores.get("credibility") or 0,
            scores.get("insight") or 0,
            config.credibility_multiplier,
            config.max_quality_score
        )
        
        # Compute recency score
        age = days_since(ep.get("published_at", ""))
        rec_score = recency_score(age, config.recency_lambda)
        
        # Compute blended final score
        if cold_start:
            # Cold start: weight quality and recency more heavily
            final = 0.0 * sim_score + 0.6 * qual_score + 0.4 * rec_score
        else:
            final = (
                config.weight_similarity * sim_score +
                config.weight_quality * qual_score +
                config.weight_recency * rec_score
            )
        
        scored.append(ScoredEpisode(
            episode=ep,
            similarity_score=sim_score,
            quality_score=qual_score,
            recency_score=rec_score,
            final_score=final
        ))
    
    # Sort by final score descending
    scored.sort(key=lambda x: x.final_score, reverse=True)
    
    return scored


# ============================================================================
# Session Management
# ============================================================================

@dataclass
class RecommendationSession:
    """A recommendation session with pre-computed ranked queue."""
    session_id: str
    queue: List[ScoredEpisode]
    shown_indices: Set[int]
    engaged_ids: Set[str]
    excluded_ids: Set[str]
    created_at: str
    cold_start: bool
    user_vector_episodes: int
    config: RecommendationConfig


def create_recommendation_queue(
    engagements: List[Dict],
    excluded_ids: Set[str],
    episodes: List[Dict],
    embeddings: Dict[str, List[float]],
    episode_by_content_id: Dict[str, Dict],
    config: RecommendationConfig = DEFAULT_CONFIG
) -> Tuple[List[ScoredEpisode], bool, int]:
    """
    Create a ranked recommendation queue.
    
    Returns:
        - queue: List of ScoredEpisode sorted by final_score
        - cold_start: Whether this is a cold start (no engagements)
        - user_vector_episodes: Number of engagements used for user vector
    """
    # Get candidate pool
    candidates = get_candidate_pool(excluded_ids, episodes, config)
    
    # Determine cold start
    cold_start = not engagements
    user_vector_episodes = min(len(engagements), config.user_vector_limit) if engagements else 0
    
    # Rank all candidates
    queue = rank_candidates(
        engagements, candidates, embeddings, episode_by_content_id, config
    )
    
    return queue, cold_start, user_vector_episodes


# ============================================================================
# Utility: Badges
# ============================================================================

def get_badges(ep: Dict) -> List[str]:
    """
    Determine badges for an episode based on its scores.
    
    Note: critical_views was removed from schema (only 11 episodes had it).
    Badges are now purely score-based.
    """
    badges = []
    scores = ep.get("scores", {})
    
    if (scores.get("insight") or 0) >= 3:
        badges.append("high_insight")
    if (scores.get("credibility") or 0) >= 3:
        badges.append("high_credibility")
    if (scores.get("information") or 0) >= 3:
        badges.append("data_rich")
    if (scores.get("entertainment") or 0) >= 3:
        badges.append("engaging")
    
    return badges[:2]  # Max 2 badges
