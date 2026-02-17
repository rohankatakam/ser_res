"""
Engagement Store abstraction.

Supplies user engagements (bookmarks, views) for session creation and
persists new engagements. Implementations: request-only (harness/eval),
Firestore (production). Swap via config for local vs cloud.
"""

from typing import List, Optional, Protocol


class EngagementStore(Protocol):
    """Protocol for user engagement read/write. Implement for request-only or Firestore."""

    def get_engagements_for_session(
        self,
        user_id: Optional[str],
        request_engagements: List[dict],
    ) -> List[dict]:
        """
        Return engagements to use for this session.
        May merge request body with stored engagements (e.g. Firestore) when user_id is set.
        """
        ...

    def record_engagement(
        self,
        user_id: Optional[str],
        episode_id: str,
        engagement_type: str,
        timestamp: Optional[str] = None,
    ) -> None:
        """Persist one engagement (e.g. bookmark, view). No-op for request-only store."""
        ...


class RequestOnlyEngagementStore:
    """
    Engagement store that uses only the request body (no persistence).
    Used for local testing, evaluation, and the test harness.
    """

    def get_engagements_for_session(
        self,
        user_id: Optional[str],
        request_engagements: List[dict],
    ) -> List[dict]:
        return list(request_engagements)

    def record_engagement(
        self,
        user_id: Optional[str],
        episode_id: str,
        engagement_type: str,
        timestamp: Optional[str] = None,
    ) -> None:
        pass
