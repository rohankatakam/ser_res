"""
Data Loading Module for Serafis Recommendation API

Handles loading and caching of episodes, series, users, and embeddings.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# ============================================================================
# Configuration
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_episodes() -> List[Dict]:
    """Load all episodes from JSON file."""
    with open(DATA_DIR / "episodes.json") as f:
        return json.load(f)


def load_series() -> List[Dict]:
    """Load all series from JSON file."""
    with open(DATA_DIR / "series.json") as f:
        return json.load(f)


def load_users() -> Dict[str, Dict]:
    """Load mock users, keyed by ID."""
    with open(DATA_DIR / "mock_users.json") as f:
        users = json.load(f)
        return {u["id"]: u for u in users}


def load_embeddings() -> Dict[str, List[float]]:
    """Load pre-computed embeddings if available."""
    embeddings_file = DATA_DIR / "embeddings.json"
    if embeddings_file.exists():
        with open(embeddings_file) as f:
            return json.load(f)
    return {}


# ============================================================================
# Data Cache (singleton pattern)
# ============================================================================

class DataCache:
    """
    Singleton cache for all loaded data.
    
    Usage:
        cache = DataCache.get_instance()
        episodes = cache.episodes
    """
    _instance: Optional["DataCache"] = None
    
    def __init__(self):
        self._episodes: Optional[List[Dict]] = None
        self._series: Optional[List[Dict]] = None
        self._users: Optional[Dict[str, Dict]] = None
        self._embeddings: Optional[Dict[str, List[float]]] = None
        
        # Derived lookups
        self._episode_map: Optional[Dict[str, Dict]] = None
        self._episode_by_content_id: Optional[Dict[str, Dict]] = None
        self._series_map: Optional[Dict[str, Dict]] = None
    
    @classmethod
    def get_instance(cls) -> "DataCache":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = DataCache()
            cls._instance._load_all()
        return cls._instance
    
    @classmethod
    def reload(cls) -> "DataCache":
        """Force reload all data."""
        cls._instance = None
        return cls.get_instance()
    
    def _load_all(self):
        """Load all data into cache."""
        self._episodes = load_episodes()
        self._series = load_series()
        self._users = load_users()
        self._embeddings = load_embeddings()
        
        # Build derived lookups
        self._episode_map = {ep["id"]: ep for ep in self._episodes}
        self._episode_by_content_id = {ep["content_id"]: ep for ep in self._episodes}
        self._series_map = {s["id"]: s for s in self._series}
        
        print(f"DataCache loaded: {len(self._episodes)} episodes, "
              f"{len(self._series)} series, {len(self._embeddings)} embeddings")
    
    @property
    def episodes(self) -> List[Dict]:
        return self._episodes or []
    
    @property
    def series(self) -> List[Dict]:
        return self._series or []
    
    @property
    def users(self) -> Dict[str, Dict]:
        return self._users or {}
    
    @property
    def embeddings(self) -> Dict[str, List[float]]:
        return self._embeddings or {}
    
    @property
    def episode_map(self) -> Dict[str, Dict]:
        return self._episode_map or {}
    
    @property
    def episode_by_content_id(self) -> Dict[str, Dict]:
        return self._episode_by_content_id or {}
    
    @property
    def series_map(self) -> Dict[str, Dict]:
        return self._series_map or {}
    
    def get_episode(self, episode_id: str) -> Optional[Dict]:
        """Get episode by ID or content_id."""
        if episode_id in self.episode_map:
            return self.episode_map[episode_id]
        if episode_id in self.episode_by_content_id:
            return self.episode_by_content_id[episode_id]
        return None
    
    def get_embedding(self, episode_id: str) -> Optional[List[float]]:
        """Get embedding for an episode by ID or content_id."""
        if episode_id in self.embeddings:
            return self.embeddings[episode_id]
        
        # Try to resolve content_id to ID
        if episode_id in self.episode_by_content_id:
            real_id = self.episode_by_content_id[episode_id]["id"]
            return self.embeddings.get(real_id)
        
        return None
