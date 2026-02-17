"""
Per-candidate blended scoring: quality, recency, and optional similarity.

Builds a ScoredEpisode for one candidate given its similarity score and config;
handles cold-start vs normal weight blend.
"""

from models.config import RecommendationConfig
from models.episode import Episode
from models.scoring import ScoredEpisode, days_since, quality_score, recency_score


def build_scored_episode(
    episode: Episode,
    sim_score: float,
    config: RecommendationConfig,
    cold_start: bool,
) -> ScoredEpisode:
    """
    Compute quality and recency scores for one episode and blend with similarity.

    Cold start: final = cold_start_weight_quality * quality + cold_start_weight_recency * recency.
    Otherwise: final = weight_similarity * sim + weight_quality * quality + weight_recency * recency.
    """
    scores = episode.get_scores()
    qual_score = quality_score(
        scores.get("credibility") or 0,
        scores.get("insight") or 0,
        config.credibility_multiplier,
        config.max_quality_score,
    )
    age = days_since(episode.published_at or "")
    rec_score = recency_score(age, config.recency_lambda)

    if cold_start:
        final = (
            config.cold_start_weight_quality * qual_score
            + config.cold_start_weight_recency * rec_score
        )
    else:
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
