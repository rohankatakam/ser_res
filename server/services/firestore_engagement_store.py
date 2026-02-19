"""
Firestore engagement store: per-user engagements in users/{user_id}/engagements.

Used when DATA_SOURCE=firebase. Reuses the same Firebase app as FirestoreUserStore
and FirestoreEpisodeProvider (same credentials_path and project_id).
Supports async via google.cloud.firestore.AsyncClient for parallel session create.
"""

import json
from pathlib import Path
from typing import Any, List, Optional, Union


def _project_id_from_credentials_file(credentials_path: Union[Path, str]) -> Optional[str]:
    """Read project_id from a Google service account JSON file if present."""
    try:
        path = Path(credentials_path)
        if not path.is_file():
            return None
        with open(path) as f:
            data = json.load(f)
        return data.get("project_id") or data.get("projectId")
    except Exception:
        return None

# Limit for get_engagements_for_ranking (most recent N)
ENGAGEMENTS_READ_LIMIT = 500

# Optional async client (used when available for parallel fetches)
try:
    from google.cloud.firestore import AsyncClient
    from google.cloud.firestore_v1.query import Query as FirestoreQuery
    from google.oauth2 import service_account
    _HAS_ASYNC_FIRESTORE = True
except ImportError:
    _HAS_ASYNC_FIRESTORE = False
    AsyncClient = None
    FirestoreQuery = None
    service_account = None


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
        self._project_id = project_id
        self._credentials_path = str(Path(credentials_path).resolve()) if credentials_path else None
        self._async_db: Any
        if not _HAS_ASYNC_FIRESTORE:
            raise ImportError(
                "FirestoreEngagementStore requires google.cloud.firestore.AsyncClient"
            )
        if not credentials_path:
            raise ValueError("FirestoreEngagementStore requires credentials_path for async Firestore")
        creds = service_account.Credentials.from_service_account_file(self._credentials_path)
        proj = project_id or _project_id_from_credentials_file(self._credentials_path)
        self._async_db = AsyncClient(project=proj, credentials=creds)

    def _engagements_ref(self, user_id: str):
        """Reference to users/{user_id}/engagements subcollection."""
        from firebase_admin import firestore
        return self._db.collection("users").document(user_id).collection("engagements")

    async def get_engagements_for_ranking_async(
        self,
        user_id: Optional[str],
        request_engagements: List[dict],
    ) -> List[dict]:
        """Async-only: Firestore read via AsyncClient."""
        if user_id is None or not user_id.strip():
            return list(request_engagements)
        ref = self._async_db.collection("users").document(user_id.strip()).collection("engagements")
        query = ref.order_by("timestamp", direction=FirestoreQuery.DESCENDING).limit(ENGAGEMENTS_READ_LIMIT)
        out = []
        async for doc in query.stream():
            d = doc.to_dict()
            out.append({
                "id": doc.id,
                "episode_id": d.get("episode_id", ""),
                "type": d.get("type", "click"),
                "timestamp": d.get("timestamp", ""),
                "episode_title": d.get("episode_title", ""),
                "series_name": d.get("series_name", ""),
            })
        return out

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
                "id": doc.id,
                "episode_id": d.get("episode_id", ""),
                "type": d.get("type", "click"),
                "timestamp": d.get("timestamp", ""),
                "episode_title": d.get("episode_title", ""),
                "series_name": d.get("series_name", ""),
            })
        return out

    def record_engagement(
        self,
        user_id: Optional[str],
        episode_id: str,
        engagement_type: str,
        timestamp: Optional[str] = None,
        episode_title: Optional[str] = None,
        series_name: Optional[str] = None,
    ) -> None:
        """Persist one engagement to users/{user_id}/engagements. No-op if user_id is None."""
        if user_id is None or not user_id.strip():
            return
        import datetime
        uid = user_id.strip()
        ref = self._engagements_ref(uid)
        ts = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        data = {
            "episode_id": episode_id,
            "type": engagement_type or "click",
            "timestamp": ts,
        }
        if episode_title is not None:
            data["episode_title"] = episode_title
        if series_name is not None:
            data["series_name"] = series_name
        try:
            ref.add(data)
        except Exception as e:
            print(f"[FirestoreEngagementStore] record_engagement failed for user={uid!r}: {e}")
            raise

    def delete_engagement(self, user_id: Optional[str], engagement_id: str) -> bool:
        """Delete one engagement document by id. Returns True if deleted."""
        if not user_id or not user_id.strip() or not engagement_id or not engagement_id.strip():
            return False
        ref = self._engagements_ref(user_id.strip())
        doc_ref = ref.document(engagement_id.strip())
        doc = doc_ref.get()
        if not doc.exists:
            return False
        doc_ref.delete()
        return True

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
