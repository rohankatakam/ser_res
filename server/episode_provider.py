"""
Episode Provider abstraction.

Supplies episode catalog and series to the recommendation engine.
Implementations: dataset (file-based), Firestore (cloud). Swap via config for
local testing vs production.
"""

from typing import Dict, List, Optional, Protocol

# Avoid circular import: LoadedDataset is from dataset_loader
try:
    from .dataset_loader import LoadedDataset
except ImportError:
    # Docker: files are copied flat into /app, so use absolute import
    from dataset_loader import LoadedDataset


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
