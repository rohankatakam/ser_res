"""
Embedding Cache Manager

Manages cached embeddings keyed by algorithm version + strategy version + dataset version.
This ensures embeddings are regenerated when either the algorithm's embedding strategy
or the dataset changes.

Cache key format: {algorithm_version}_s{strategy_version}__{dataset_version}
Example: v1_2_blended_s1.0__eval_909_feb2026

Cache files are stored as JSON in the cache/embeddings/ directory.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingCacheMetadata:
    """Metadata about a cached embedding file."""
    algorithm_version: str
    strategy_version: str
    dataset_version: str
    embedding_model: str
    embedding_dimensions: int
    created_at: str
    episode_count: int
    cache_key: str


class EmbeddingCache:
    """
    Manages embedding cache for algorithm+dataset combinations.
    
    Usage:
        cache = EmbeddingCache(cache_dir)
        
        # Check if embeddings exist
        if cache.has_cache("v1_2_blended", "1.0", "eval_909_feb2026"):
            embeddings = cache.load_embeddings(...)
        else:
            # Generate and save
            cache.save_embeddings(..., embeddings)
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize the embedding cache.
        
        Args:
            cache_dir: Directory to store cache files (typically cache/embeddings/)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> str:
        """
        Generate cache key for an algorithm+dataset combination.
        
        The key includes strategy_version to ensure embeddings are regenerated
        when the embedding logic changes.
        """
        # Sanitize versions for filename
        algo = algorithm_version.replace("/", "_").replace("\\", "_")
        strat = strategy_version.replace(".", "_")
        data = dataset_version.replace("/", "_").replace("\\", "_")
        return f"{algo}_s{strat}__{data}"
    
    def get_cache_path(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> Path:
        """Get the file path for a cache entry."""
        key = self.get_cache_key(algorithm_version, strategy_version, dataset_version)
        return self.cache_dir / f"{key}.json"
    
    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> bool:
        """Check if embeddings are cached for this combination."""
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        return path.exists()
    
    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> Optional[Dict[str, List[float]]]:
        """
        Load cached embeddings for an algorithm+dataset combination.
        
        Returns:
            Dict mapping episode_id to embedding vector, or None if not cached
        """
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        
        if not path.exists():
            return None
        
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("embeddings", {})
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load embeddings from {path}: {e}")
            return None
    
    def load_metadata(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> Optional[EmbeddingCacheMetadata]:
        """
        Load metadata about cached embeddings.
        
        Returns:
            EmbeddingCacheMetadata or None if not cached
        """
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        
        if not path.exists():
            return None
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            return EmbeddingCacheMetadata(
                algorithm_version=data.get("algorithm_version", ""),
                strategy_version=data.get("strategy_version", ""),
                dataset_version=data.get("dataset_version", ""),
                embedding_model=data.get("embedding_model", ""),
                embedding_dimensions=data.get("embedding_dimensions", 0),
                created_at=data.get("created_at", ""),
                episode_count=data.get("episode_count", 0),
                cache_key=self.get_cache_key(
                    algorithm_version, strategy_version, dataset_version
                )
            )
        except (json.JSONDecodeError, IOError):
            return None
    
    def save_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int
    ) -> Path:
        """
        Save embeddings to cache.
        
        Args:
            algorithm_version: Version of the algorithm (e.g., "v1_2_blended")
            strategy_version: Version of the embedding strategy (e.g., "1.0")
            dataset_version: Version of the dataset (e.g., "eval_909_feb2026")
            embeddings: Dict mapping episode_id to embedding vector
            embedding_model: Name of the embedding model used
            embedding_dimensions: Dimensionality of embeddings
        
        Returns:
            Path to the saved cache file
        """
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        
        data = {
            "algorithm_version": algorithm_version,
            "strategy_version": strategy_version,
            "dataset_version": dataset_version,
            "embedding_model": embedding_model,
            "embedding_dimensions": embedding_dimensions,
            "created_at": datetime.now().isoformat(),
            "episode_count": len(embeddings),
            "embeddings": embeddings
        }
        
        with open(path, "w") as f:
            json.dump(data, f)
        
        print(f"Saved {len(embeddings)} embeddings to {path}")
        return path
    
    def delete_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> bool:
        """
        Delete cached embeddings.
        
        Returns:
            True if file was deleted, False if it didn't exist
        """
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list_cached(self) -> List[EmbeddingCacheMetadata]:
        """
        List all cached embedding files.
        
        Returns:
            List of EmbeddingCacheMetadata for each cached file
        """
        results = []
        
        for path in self.cache_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                
                results.append(EmbeddingCacheMetadata(
                    algorithm_version=data.get("algorithm_version", ""),
                    strategy_version=data.get("strategy_version", ""),
                    dataset_version=data.get("dataset_version", ""),
                    embedding_model=data.get("embedding_model", ""),
                    embedding_dimensions=data.get("embedding_dimensions", 0),
                    created_at=data.get("created_at", ""),
                    episode_count=data.get("episode_count", 0),
                    cache_key=path.stem
                ))
            except (json.JSONDecodeError, IOError):
                continue
        
        return results
    
    def get_cache_size_bytes(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> int:
        """Get the size of a cache file in bytes."""
        path = self.get_cache_path(algorithm_version, strategy_version, dataset_version)
        
        if path.exists():
            return path.stat().st_size
        return 0
