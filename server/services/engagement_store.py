"""
Engagement Store abstraction.

Supplies user engagements (bookmarks, views) for session creation and
persists new engagements. Implementations: request-only (harness/eval),
Firestore (production). Swap via config for local vs cloud.
"""

from typing import List, Optional, Protocol


class EngagementStore(Protocol):
    """Protocol for user engagement read/write. Implement for request-only or Firestore."""

    def get_engagements_for_ranking(
        self,
        user_id: Optional[str],
        request_engagements: List[dict],
    ) -> List[dict]:
        """
        Return engagements to use for ranking this request.
        When user_id is set, returns all (or recent) engagements for that user from the store
        (e.g. Firestore users/{user_id}/engagements) as source of truth. When user_id is None,
        returns request_engagements only.
        """
        ...

    def record_engagement(
        self,
        user_id: Optional[str],
        episode_id: str,
        engagement_type: str,
        timestamp: Optional[str] = None,
        episode_title: Optional[str] = None,
        series_name: Optional[str] = None,
    ) -> None:
        """Persist one engagement (e.g. bookmark, view). No-op for request-only store."""
        ...

    def delete_engagement(self, user_id: Optional[str], engagement_id: str) -> bool:
        """Delete one engagement by Firestore document id. Return True if deleted. No-op for request-only store."""
        ...

    def delete_all_engagements(self, user_id: Optional[str]) -> None:
        """Delete all engagements for the user (e.g. for Reset). No-op for request-only store."""
        ...


class RequestOnlyEngagementStore:
    """
    Engagement store that uses only the request body (no persistence).
    Used for local testing, evaluation, and the test harness.
    """

    def get_engagements_for_ranking(
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
        episode_title: Optional[str] = None,
        series_name: Optional[str] = None,
    ) -> None:
        pass

    def delete_engagement(self, user_id: Optional[str], engagement_id: str) -> bool:
        return False

    def delete_all_engagements(self, user_id: Optional[str]) -> None:
        pass
