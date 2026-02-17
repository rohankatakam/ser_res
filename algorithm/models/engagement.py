"""
Engagement model — user interaction with an episode (click, listen, bookmark).

Used by the ranking stage for user vector and similarity scoring.
Built from API/Firebase dicts via Engagement.model_validate(d) or ensure_engagements().
"""

from typing import Dict, List, Union

from pydantic import BaseModel, ConfigDict


class Engagement(BaseModel):
    """
    A single user engagement (e.g. click, listen, bookmark) on an episode.

    episode_id: content or episode id (may be resolved to internal id via episode_by_content_id).
    timestamp: sort key (ISO string); newest first for user vector.
    type: engagement type used for weighting (e.g. "click", "listen", "bookmark").
    """

    model_config = ConfigDict(extra="allow")

    episode_id: str = ""
    timestamp: str = ""
    type: str = "click"


def ensure_engagements(
    items: List[Union[Dict, "Engagement"]],
) -> List["Engagement"]:
    """Convert list of dicts or Engagements to list of Engagement models for the pipeline."""
    return [
        Engagement.model_validate(e) if isinstance(e, dict) else e
        for e in items
    ]
