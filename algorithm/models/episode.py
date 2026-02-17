"""
Episode model — typed representation of an episode for the recommendation pipeline.

Used by candidate_pool, semantic_scoring, and embedding stages instead of raw dicts.
Built from dataset/API dicts via Episode.model_validate(d).
"""

from typing import Any, Dict, List, Optional

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
