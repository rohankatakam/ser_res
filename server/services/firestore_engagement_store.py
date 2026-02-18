"""
Firestore engagement store: per-user engagements in users/{user_id}/engagements.

Used when DATA_SOURCE=firebase. Reuses the same Firebase app as FirestoreUserStore
and FirestoreEpisodeProvider (same credentials_path and project_id).
"""

from typing import List, Optional, Union
from pathlib import Path

# Limit for get_engagements_for_ranking (most recent N)
ENGAGEMENTS_READ_LIMIT = 500


class FirestoreEngagementStore:
    """
    Engagement store backed by Firestore subcollection users/{user_id}/engagements.
    Each document: { episode_id, type, timestamp }. Document ID: auto-generated.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[Union[Path, str]] = None,
    ):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError:
            raise ImportError(
                "firebase-admin is required for FirestoreEngagementStore. pip install firebase-admin"
            )
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(str(Path(credentials_path).resolve()))
                opts = {"projectId": project_id} if project_id else None
                firebase_admin.initialize_app(cred, opts)
            else:
                firebase_admin.initialize_app(options={"projectId": project_id} if project_id else None)
        self._db = firestore.client()

    def _engagements_ref(self, user_id: str):
        """Reference to users/{user_id}/engagements subcollection."""
        from firebase_admin import firestore
        return self._db.collection("users").document(user_id).collection("engagements")

    def get_engagements_for_ranking(
        self,
        user_id: Optional[str],
        request_engagements: List[dict],
    ) -> List[dict]:
        """
        Return engagements to use for ranking this session.
        If user_id is None, return request_engagements only.
        If user_id is set, read from users/{user_id}/engagements (order by timestamp desc, limit 500)
        and return those as source of truth; request_engagements are ignored for stored users.
        """
        if user_id is None or not user_id.strip():
            return list(request_engagements)
        from firebase_admin import firestore
        ref = self._engagements_ref(user_id.strip())
        query = ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(ENGAGEMENTS_READ_LIMIT)
        docs = query.stream()
        out = []
        for doc in docs:
            d = doc.to_dict()
            out.append({
                "episode_id": d.get("episode_id", ""),
                "type": d.get("type", "click"),
                "timestamp": d.get("timestamp", ""),
            })
        return out

    def record_engagement(
        self,
        user_id: Optional[str],
        episode_id: str,
        engagement_type: str,
        timestamp: Optional[str] = None,
    ) -> None:
        """Persist one engagement to users/{user_id}/engagements. No-op if user_id is None."""
        if user_id is None or not user_id.strip():
            return
        import datetime
        uid = user_id.strip()
        ref = self._engagements_ref(uid)
        ts = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        try:
            ref.add({
                "episode_id": episode_id,
                "type": engagement_type or "click",
                "timestamp": ts,
            })
        except Exception as e:
            print(f"[FirestoreEngagementStore] record_engagement failed for user={uid!r}: {e}")
            raise

    def delete_all_engagements(self, user_id: Optional[str]) -> None:
        """Delete all documents in users/{user_id}/engagements (batch delete in chunks)."""
        if not user_id or not user_id.strip():
            return
        ref = self._engagements_ref(user_id.strip())
        batch_size = 500
        while True:
            docs = ref.limit(batch_size).stream()
            to_delete = list(docs)
            if not to_delete:
                break
            batch = self._db.batch()
            for doc in to_delete:
                batch.delete(doc.reference)
            batch.commit()
