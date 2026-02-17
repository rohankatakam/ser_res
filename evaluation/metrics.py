#!/usr/bin/env python3
"""
Quantitative Metrics for Recommendation Evaluation

Computes industry-standard metrics:
- Precision@K
- Coverage
- Diversity (intra-list, both entropy-based and embedding-based ILD)
- Average scores (similarity, quality, recency)

Usage:
    from metrics import compute_metrics
    metrics = compute_metrics(response, all_episodes)

TODO (Future Metrics - requires additional data):
- Novelty (Long-tail) Score: Measures how many recommendations come from
  the "long-tail" (low global visit counts). Formula: novelty = 1 - normalized_popularity
  Requires: Global visit/engagement counts per episode (not currently available)

- Serendipity Score: Measures "unexpected relevance" - items that are highly
  relevant but dissimilar to user's typical interests.
  Requires: Clear threshold definitions and possibly user feedback data
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Set
from collections import Counter


def compute_precision_at_k(
    recommended_ids: List[str],
    relevant_ids: Set[str],
    k: int = 10
) -> float:
    """
    Compute Precision@K.
    
    In the absence of ground truth relevance labels, we use category matching
    or quality thresholds as a proxy for relevance.
    
    Args:
        recommended_ids: List of recommended episode IDs
        relevant_ids: Set of episode IDs considered "relevant"
        k: Number of top recommendations to consider
    
    Returns:
        Precision@K value between 0 and 1
    """
    if k == 0:
        return 0.0
    
    top_k = recommended_ids[:k]
    hits = sum(1 for eid in top_k if eid in relevant_ids)
    return hits / k


def compute_ndcg_at_k(
    recommended_ids: List[str],
    relevance_scores: Dict[str, float],
    k: int = 10
) -> float:
    """
    Compute Normalized Discounted Cumulative Gain (NDCG@K).
    
    Args:
        recommended_ids: List of recommended episode IDs
        relevance_scores: Dict mapping episode ID to relevance score
        k: Number of top recommendations to consider
    
    Returns:
        NDCG@K value between 0 and 1
    """
    def dcg(scores: List[float]) -> float:
        return sum(
            score / math.log2(i + 2)  # i+2 because log2(1) = 0
            for i, score in enumerate(scores)
        )
    
    # Get relevance scores for recommended items
    rec_scores = [relevance_scores.get(eid, 0.0) for eid in recommended_ids[:k]]
    
    # Ideal ranking (sorted by relevance)
    ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
    
    dcg_score = dcg(rec_scores)
    idcg_score = dcg(ideal_scores)
    
    if idcg_score == 0:
        return 0.0
    
    return dcg_score / idcg_score


def compute_coverage(
    all_recommended_ids: List[str],
    total_catalog_size: int
) -> float:
    """
    Compute catalog coverage.
    
    What percentage of the catalog appears in any recommendation?
    
    Args:
        all_recommended_ids: All episode IDs that were recommended (across all sessions)
        total_catalog_size: Total number of episodes in catalog
    
    Returns:
        Coverage value between 0 and 1
    """
    unique_recommended = len(set(all_recommended_ids))
    return unique_recommended / total_catalog_size if total_catalog_size > 0 else 0.0


def compute_intra_list_diversity(
    episodes: List[Dict],
    diversity_key: str = "series"
) -> float:
    """
    Compute intra-list diversity (entropy-based).
    
    How diverse are the recommendations within a single list?
    Uses entropy of the specified key (series, category, etc.)
    
    Args:
        episodes: List of episode dicts
        diversity_key: Key to compute diversity on ("series", "category")
    
    Returns:
        Diversity score (higher = more diverse), normalized 0-1
    """
    if not episodes:
        return 0.0
    
    # Extract values for diversity key
    if diversity_key == "series":
        values = [ep.get("series", {}).get("name", "unknown") for ep in episodes]
    elif diversity_key == "category":
        values = []
        for ep in episodes:
            categories = ep.get("categories", {}).get("major", [])
            values.append(categories[0] if categories else "unknown")
    else:
        values = [ep.get(diversity_key, "unknown") for ep in episodes]
    
    # Compute entropy
    counts = Counter(values)
    total = len(values)
    
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    # Normalize by max possible entropy (uniform distribution)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    
    return entropy / max_entropy if max_entropy > 0 else 0.0


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Cosine similarity between -1 and 1 (typically 0-1 for normalized embeddings)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def compute_embedding_ild(
    episode_ids: List[str],
    embeddings: Dict[str, List[float]]
) -> float:
    """
    Compute Intra-List Diversity using embedding cosine distances.
    
    Research-grounded metric (Spotify/Netflix methodology):
    ILD(R) = (2 / n(n-1)) * Σ Σ (1 - cosine_sim(r_i, r_j))
    
    This measures the average pairwise dissimilarity between all
    recommended items using their embeddings.
    
    Args:
        episode_ids: List of recommended episode IDs (in order)
        embeddings: Dict mapping episode_id -> embedding vector
    
    Returns:
        ILD score between 0 and 1 (higher = more diverse)
        Returns -1.0 if insufficient embeddings available
    """
    # Filter to episodes we have embeddings for
    valid_ids = [eid for eid in episode_ids if eid in embeddings]
    n = len(valid_ids)
    
    if n < 2:
        return -1.0  # Not enough items to compute diversity
    
    # Compute pairwise cosine distances
    total_distance = 0.0
    pair_count = 0
    
    for i in range(n - 1):
        for j in range(i + 1, n):
            vec_i = embeddings[valid_ids[i]]
            vec_j = embeddings[valid_ids[j]]
            
            similarity = cosine_similarity(vec_i, vec_j)
            distance = 1.0 - similarity
            total_distance += distance
            pair_count += 1
    
    # Average pairwise distance: 2 / (n * (n-1)) * sum
    # pair_count = n*(n-1)/2, so average = total_distance / pair_count
    avg_ild = total_distance / pair_count if pair_count > 0 else 0.0
    
    return avg_ild


def compute_average_scores(episodes: List[Dict]) -> Dict[str, float]:
    """
    Compute average scores from recommendation response.
    
    Args:
        episodes: List of episode dicts with score fields
    
    Returns:
        Dict with average similarity, quality, recency, final scores
    """
    if not episodes:
        return {
            "avg_similarity": 0.0,
            "avg_quality": 0.0,
            "avg_recency": 0.0,
            "avg_final": 0.0,
            "avg_credibility": 0.0,
            "avg_insight": 0.0
        }
    
    n = len(episodes)
    
    return {
        "avg_similarity": sum(ep.get("similarity_score") or 0 for ep in episodes) / n,
        "avg_quality": sum(ep.get("quality_score") or 0 for ep in episodes) / n,
        "avg_recency": sum(ep.get("recency_score") or 0 for ep in episodes) / n,
        "avg_final": sum(ep.get("final_score") or 0 for ep in episodes) / n,
        "avg_credibility": sum(ep.get("scores", {}).get("credibility", 0) for ep in episodes) / n,
        "avg_insight": sum(ep.get("scores", {}).get("insight", 0) for ep in episodes) / n
    }


def compute_freshness(episodes: List[Dict]) -> Dict[str, float]:
    """
    Compute freshness metrics.
    
    Args:
        episodes: List of episode dicts with published_at
    
    Returns:
        Dict with freshness statistics
    """
    from datetime import datetime, timezone
    
    if not episodes:
        return {"avg_age_days": 0.0, "min_age_days": 0.0, "max_age_days": 0.0}
    
    now = datetime.now(timezone.utc)
    ages = []
    
    for ep in episodes:
        try:
            pub_date = datetime.fromisoformat(ep.get("published_at", "").replace("+00:00", "+00:00"))
            age = (now - pub_date).days
            ages.append(age)
        except:
            pass
    
    if not ages:
        return {"avg_age_days": 0.0, "min_age_days": 0.0, "max_age_days": 0.0}
    
    return {
        "avg_age_days": sum(ages) / len(ages),
        "min_age_days": min(ages),
        "max_age_days": max(ages)
    }


def compute_all_metrics(
    response: Dict, 
    catalog_size: int = 909,
    embeddings: Dict[str, List[float]] = None
) -> Dict:
    """
    Compute all metrics for a single API response.
    
    Args:
        response: API response dict with episodes
        catalog_size: Total episodes in catalog
        embeddings: Optional dict mapping episode_id -> embedding vector
                   for computing embedding-based ILD
    
    Returns:
        Dict with all computed metrics
    """
    episodes = response.get("episodes", [])
    
    metrics = {
        "episode_count": len(episodes),
        "cold_start": response.get("cold_start", False),
        "total_in_queue": response.get("total_in_queue", 0),
    }
    
    # Average scores
    metrics.update(compute_average_scores(episodes))
    
    # Diversity (entropy-based)
    metrics["series_diversity"] = compute_intra_list_diversity(episodes, "series")
    metrics["category_diversity"] = compute_intra_list_diversity(episodes, "category")
    
    # Embedding-based ILD (if embeddings provided)
    if embeddings:
        episode_ids = [ep.get("id") for ep in episodes if ep.get("id")]
        metrics["embedding_ild"] = compute_embedding_ild(episode_ids, embeddings)
    else:
        metrics["embedding_ild"] = None
    
    # Freshness
    metrics.update(compute_freshness(episodes))
    
    # Series distribution
    series_counts = Counter(ep.get("series", {}).get("name", "unknown") for ep in episodes)
    metrics["unique_series"] = len(series_counts)
    metrics["max_series_count"] = max(series_counts.values()) if series_counts else 0
    
    return metrics


def format_metrics_report(metrics: Dict) -> str:
    """Format metrics as a readable report."""
    lines = [
        "="*50,
        "RECOMMENDATION METRICS",
        "="*50,
        "",
        f"Episodes: {metrics.get('episode_count', 0)}",
        f"Cold Start: {metrics.get('cold_start', False)}",
        f"Queue Size: {metrics.get('total_in_queue', 0)}",
        "",
        "--- Scores ---",
        f"Avg Similarity: {metrics.get('avg_similarity', 0):.4f}",
        f"Avg Quality: {metrics.get('avg_quality', 0):.4f}",
        f"Avg Recency: {metrics.get('avg_recency', 0):.4f}",
        f"Avg Final: {metrics.get('avg_final', 0):.4f}",
        "",
        "--- Quality ---",
        f"Avg Credibility: {metrics.get('avg_credibility', 0):.2f}",
        f"Avg Insight: {metrics.get('avg_insight', 0):.2f}",
        "",
        "--- Diversity ---",
        f"Series Diversity (entropy): {metrics.get('series_diversity', 0):.4f}",
        f"Category Diversity (entropy): {metrics.get('category_diversity', 0):.4f}",
    ]
    
    # Add embedding ILD if available
    embedding_ild = metrics.get('embedding_ild')
    if embedding_ild is not None and embedding_ild >= 0:
        lines.append(f"Embedding ILD (cosine): {embedding_ild:.4f}")
    elif embedding_ild == -1:
        lines.append("Embedding ILD: N/A (insufficient data)")
    else:
        lines.append("Embedding ILD: N/A (no embeddings)")
    
    lines.extend([
        f"Unique Series: {metrics.get('unique_series', 0)}",
        f"Max from Single Series: {metrics.get('max_series_count', 0)}",
        "",
        "--- Freshness ---",
        f"Avg Age: {metrics.get('avg_age_days', 0):.1f} days",
        f"Newest: {metrics.get('min_age_days', 0):.0f} days",
        f"Oldest: {metrics.get('max_age_days', 0):.0f} days",
        "="*50,
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage
    import requests
    
    API_URL = "http://localhost:8000"
    
    # Test with cold start
    response = requests.post(
        f"{API_URL}/api/sessions/create",
        json={"engagements": [], "excluded_ids": []}
    )
    
    if response.ok:
        data = response.json()
        metrics = compute_all_metrics(data)
        print(format_metrics_report(metrics))
    else:
        print(f"API error: {response.status_code}")
