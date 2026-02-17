"""
Episode Provider abstraction.

Supplies episode catalog and series to the recommendation engine.
Implementations: dataset (file-based), HTTP mock/Firestore API, Firestore (cloud).
"""

from typing import Dict, List, Optional, Protocol

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
