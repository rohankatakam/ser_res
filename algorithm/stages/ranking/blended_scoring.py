"""
Per-candidate blended scoring: similarity, quality, and recency.

Builds a ScoredEpisode for one candidate using the unified formula for all cases.
"""

from models.config import RecommendationConfig
from models.episode import Episode
from models.scoring import ScoredEpisode, days_since, quality_score, recency_score


def build_scored_episode(
    episode: Episode,
    sim_score: float,
    config: RecommendationConfig,
) -> ScoredEpisode:
    """
    Compute final score: weight_similarity * sim + weight_quality * quality + weight_recency * recency.

    Same formula for all four user-state cases. When no user vector, sim_score=0.5 (neutral).
    """
    scores = episode.get_scores()
    qual_score = quality_score(
        scores.get("credibility") or 0,
        scores.get("insight") or 0,
        config.credibility_multiplier,
    )
    age = days_since(episode.published_at or "")
    rec_score = recency_score(age, config.recency_lambda)

    final = (
        config.weight_similarity * sim_score
        + config.weight_quality * qual_score
        + config.weight_recency * rec_score
    )
    return ScoredEpisode(
        episode=episode,
        similarity_score=sim_score,
        quality_score=qual_score,
        recency_score=rec_score,
        final_score=final,
    )
