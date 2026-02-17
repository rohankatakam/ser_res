"""
Episode model — typed representation of an episode for the recommendation pipeline.

Used by candidate_pool, ranking (Stage B), and embedding stages instead of raw dicts.
Built from dataset/API dicts via Episode.model_validate(d).
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict


class Episode(BaseModel):
    """
    Episode payload used across the algorithm stages.

    All fields except id are optional to support partial data from datasets/APIs.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    content_id: Optional[str] = ""
    title: Optional[str] = ""
    published_at: Optional[str] = ""
    scores: Optional[Dict[str, Any]] = None
    key_insight: Optional[str] = None
    categories: Optional[Dict[str, Any]] = None
    series: Optional[Dict[str, Any]] = None

    def get_scores(self) -> Dict[str, Any]:
        """Scores dict, never None."""
        return self.scores if self.scores is not None else {}

    @property
    def credibility(self) -> int:
        """Convenience for scores.credibility."""
        return self.get_scores().get("credibility") or 0

    @property
    def insight(self) -> int:
        """Convenience for scores.insight."""
        return self.get_scores().get("insight") or 0

    def get_primary_category(self) -> Optional[str]:
        """Primary (first) major category for this episode."""
        categories = self.categories if self.categories is not None else {}
        major: List[str] = categories.get("major", []) if isinstance(categories, dict) else []
        return major[0] if major else None


def ensure_list(episodes: List[Union[Dict[str, Any], "Episode"]]) -> List["Episode"]:
    """Convert list of dicts or Episodes to list of Episode models for use in the pipeline."""
    return [
        Episode.model_validate(e) if isinstance(e, dict) else e
        for e in episodes
    ]


def ensure_episode_by_content_id(
    episode_by_content_id: Dict[str, Union[Dict[str, Any], "Episode"]],
) -> Dict[str, "Episode"]:
    """Convert episode_by_content_id values to Episode models."""
    return {
        k: Episode.model_validate(v) if isinstance(v, dict) else v
        for k, v in episode_by_content_id.items()
    }
