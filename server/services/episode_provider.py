"""
Episode Provider abstraction.

Supplies episode catalog and series to the recommendation engine.
Implementations: dataset (file-based), JSON paths, HTTP mock/Firestore API, Firestore (cloud).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

import requests

from .dataset_loader import LoadedDataset


class EpisodeProvider(Protocol):
    """Protocol for episode catalog access. Implement for dataset (file) or Firestore."""

    def get_episodes(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
        episode_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Return episodes, optionally filtered/paginated.
        limit=None means return all (subject to implementation limits).
        """
        ...

    def get_episode(self, episode_id: str) -> Optional[Dict]:
        """Get one episode by id or content_id."""
        ...

    def get_series(self) -> List[Dict]:
        """Return series list (for UI/discovery)."""
        ...

    def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
        """Map content_id -> episode for engagement resolution."""
        ...


class DatasetEpisodeProvider:
    """
    Episode provider backed by a LoadedDataset (file-based).
    Used for local testing and evaluation.
    """

    def __init__(self, dataset: "LoadedDataset"):
        if not hasattr(dataset, "episodes") or not hasattr(dataset, "episode_by_content_id"):
            raise TypeError("dataset must have episodes and episode_by_content_id (e.g. LoadedDataset)")
        self._dataset = dataset

    def get_episodes(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
        episode_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        episodes = self._dataset.episodes
        if episode_ids is not None:
            id_set = set(episode_ids)
            episodes = [e for e in episodes if e.get("id") in id_set or e.get("content_id") in id_set]
        if since or until:
            # Optional: filter by published_at if needed later
            pass
        if offset:
            episodes = episodes[offset:]
        if limit is not None:
            episodes = episodes[:limit]
        return episodes

    def get_episode(self, episode_id: str) -> Optional[Dict]:
        return self._dataset.get_episode(episode_id)

    def get_series(self) -> List[Dict]:
        return self._dataset.series

    def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
        return self._dataset.episode_by_content_id


class JsonEpisodeProvider:
    """
    Episode provider backed by JSON files (episodes.json, series.json).
    Used when DATA_SOURCE=json; paths come from EPISODES_JSON_PATH and SERIES_JSON_PATH.
    """

    def __init__(self, episodes_path: Union[Path, str], series_path: Union[Path, str]):
        self._episodes_path = Path(episodes_path)
        self._series_path = Path(series_path)
        if not self._episodes_path.exists():
            raise FileNotFoundError(f"Episodes JSON not found: {self._episodes_path}")
        with open(self._episodes_path) as f:
            self._episodes = json.load(f)
        self._episode_by_id = {e.get("id"): e for e in self._episodes if e.get("id")}
        self._episode_by_content_id = {
            e["content_id"]: e for e in self._episodes if e.get("content_id")
        }
        self._series: List[Dict] = []
        if self._series_path.exists():
            with open(self._series_path) as f:
                self._series = json.load(f)

    def get_episodes(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
        episode_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        episodes = list(self._episodes)
        if episode_ids is not None:
            id_set = set(episode_ids)
            episodes = [e for e in episodes if e.get("id") in id_set or e.get("content_id") in id_set]
        if since:
            episodes = [e for e in episodes if (e.get("published_at") or "") >= since]
        if until:
            episodes = [e for e in episodes if (e.get("published_at") or "") <= until]
        episodes.sort(key=lambda e: e.get("published_at") or "", reverse=True)
        if offset:
            episodes = episodes[offset:]
        if limit is not None:
            episodes = episodes[:limit]
        return episodes

    def get_episode(self, episode_id: str) -> Optional[Dict]:
        if episode_id in self._episode_by_id:
            return self._episode_by_id[episode_id]
        return self._episode_by_content_id.get(episode_id)

    def get_series(self) -> List[Dict]:
        return self._series

    def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
        return self._episode_by_content_id


class HttpEpisodeProvider:
    """
    Episode provider that calls a Firestore-like HTTP API (e.g. mock_episodes_api).
    Use for testing the same contract as production without Firestore.
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._content_id_map_cache: Optional[Dict[str, Dict]] = None

    def get_episodes(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
        episode_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        params = {"offset": offset}
        if limit is not None:
            params["limit"] = limit
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if episode_ids:
            params["episode_ids"] = ",".join(episode_ids)
        r = requests.get(
            f"{self._base}/episodes",
            params=params,
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("episodes", [])

    def get_episode(self, episode_id: str) -> Optional[Dict]:
        r = requests.get(
            f"{self._base}/episodes/{requests.utils.quote(episode_id)}",
            timeout=self._timeout,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def get_series(self) -> List[Dict]:
        r = requests.get(f"{self._base}/series", timeout=self._timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("series", [])

    def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
        if self._content_id_map_cache is not None:
            return self._content_id_map_cache
        # Prefer dedicated endpoint if available
        r = requests.get(
            f"{self._base}/episode-by-content-id-map",
            timeout=self._timeout,
        )
        if r.status_code == 200:
            self._content_id_map_cache = r.json()
            return self._content_id_map_cache
        # Fallback: fetch all episodes and build map
        episodes = self.get_episodes(limit=99999)
        self._content_id_map_cache = {
            e["content_id"]: e for e in episodes if e.get("content_id")
        }
        return self._content_id_map_cache


class FirestoreEpisodeProvider:
    """
    Episode provider backed by Cloud Firestore.

    Uses collections: episodes (doc id = episode id), series (doc id = series id).
    For get_episodes with since/until or order_by, create a composite index in the
    Firebase Console: episodes collection, field published_at (Descending).
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
                "firebase-admin is required for FirestoreEpisodeProvider. pip install firebase-admin"
            )
        self._project_id = project_id
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(str(Path(credentials_path).resolve()))
                opts = {"projectId": project_id} if project_id else None
                firebase_admin.initialize_app(cred, opts)
            else:
                firebase_admin.initialize_app(options={"projectId": project_id} if project_id else None)
        self._db = firestore.client()
        self._episodes_coll = self._db.collection("episodes")
        self._series_coll = self._db.collection("series")
        self._content_id_map_cache: Optional[Dict[str, Dict]] = None

    def _doc_to_dict(self, doc: Any) -> Dict:
        d = doc.to_dict()
        d["id"] = doc.id
        return d

    def get_episodes(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
        episode_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        from firebase_admin import firestore

        if episode_ids is not None:
            out = []
            for eid in episode_ids:
                doc = self._episodes_coll.document(eid).get()
                if doc.exists:
                    out.append(self._doc_to_dict(doc))
            if offset:
                out = out[offset:]
            if limit is not None:
                out = out[:limit]
            return out

        query = self._episodes_coll
        if since:
            query = query.where("published_at", ">=", since)
        if until:
            query = query.where("published_at", "<=", until)
        query = query.order_by(
            "published_at", direction=firestore.Query.DESCENDING
        )
        fetch_limit = (limit or 2000) + offset
        fetch_limit = min(fetch_limit, 2000)
        docs = query.limit(fetch_limit).stream()
        out = [self._doc_to_dict(d) for d in docs]
        if offset:
            out = out[offset:]
        if limit is not None:
            out = out[:limit]
        return out

    def get_episode(self, episode_id: str) -> Optional[Dict]:
        doc = self._episodes_coll.document(episode_id).get()
        if doc.exists:
            return self._doc_to_dict(doc)
        # Try by content_id (linear scan; for large collections add a content_id -> doc_id map)
        for doc in self._episodes_coll.where("content_id", "==", episode_id).limit(1).stream():
            return self._doc_to_dict(doc)
        return None

    def get_series(self) -> List[Dict]:
        docs = self._series_coll.stream()
        return [self._doc_to_dict(d) for d in docs]

    def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
        if self._content_id_map_cache is not None:
            return self._content_id_map_cache
        docs = self._episodes_coll.stream()
        self._content_id_map_cache = {}
        for doc in docs:
            d = self._doc_to_dict(doc)
            cid = d.get("content_id")
            if cid:
                self._content_id_map_cache[cid] = d
        return self._content_id_map_cache
