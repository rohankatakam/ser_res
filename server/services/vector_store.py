"""
Vector Store abstraction.

Backing store for episode embeddings. Implementations: Qdrant+JSON (local),
Pinecone (cloud). Swap via config for local testing vs production.
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol

from .embedding_cache import EmbeddingCache
from .qdrant_store import QdrantEmbeddingStore, compute_strategy_hash


class VectorStore(Protocol):
    """Protocol for embedding storage. Implement for Qdrant+JSON (local) or Pinecone (cloud)."""

    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> bool:
        """Return True if embeddings exist for this algo+strategy+dataset."""
        ...

    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        *,
        strategy_file_path: Optional[Path] = None,
    ) -> Optional[Dict[str, List[float]]]:
        """Load all embeddings for this namespace. Optional hash verification when strategy_file_path is set."""
        ...

    def get_embeddings(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        """
        Fetch embeddings only for the given episode ids (e.g. for session create).
        Cloud (Pinecone) should implement this with fetch-by-id; local may load full and filter.
        """
        ...

    def save_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        *,
        strategy_file_path: Optional[Path] = None,
    ) -> None:
        """Persist embeddings."""
        ...


class QdrantJsonVectorStore:
    """
    Vector store that uses Qdrant when available and JSON cache as fallback/backup.
    Used for local testing and evaluation. Replace with PineconeVectorStore for production.
    """

    def __init__(
        self,
        embedding_cache: "EmbeddingCache",
        qdrant_store: Optional["QdrantEmbeddingStore"] = None,
    ):
        if embedding_cache is None:
            raise ValueError("embedding_cache is required")
        self._cache = embedding_cache
        self._qdrant = qdrant_store
        self._qdrant_available = bool(qdrant_store and getattr(qdrant_store, "is_available", False))

    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> bool:
        if self._qdrant_available and self._qdrant:
            if self._qdrant.has_cache(algorithm_version, strategy_version, dataset_version):
                return True
        return self._cache.has_cache(algorithm_version, strategy_version, dataset_version)

    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        *,
        strategy_file_path: Optional[Path] = None,
    ) -> Optional[Dict[str, List[float]]]:
        if self._qdrant_available and self._qdrant and strategy_file_path and compute_strategy_hash:
            current_hash = compute_strategy_hash(strategy_file_path)
            if current_hash:
                matches, stored_hash = self._qdrant.verify_strategy_hash(
                    algorithm_version, strategy_version, dataset_version, current_hash
                )
                if not matches and stored_hash:
                    print("WARNING: embedding_strategy.py has changed; consider regenerating with force=true")
        if self._qdrant_available and self._qdrant:
            emb = self._qdrant.load_embeddings(
                algorithm_version, strategy_version, dataset_version
            )
            if emb is not None:
                return emb
        emb = self._cache.load_embeddings(
            algorithm_version, strategy_version, dataset_version
        )
        if emb and self._qdrant_available and self._qdrant:
            try:
                self._migrate_to_qdrant(
                    algorithm_version, strategy_version, dataset_version,
                    emb, strategy_file_path
                )
            except Exception as e:
                print(f"Migration to Qdrant failed: {e}")
        return emb

    def get_embeddings(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        """Fetch embeddings for given ids only. Loads full cache then filters (Pinecone impl would fetch by id)."""
        id_set = set(episode_ids)
        if not id_set:
            return {}
        full = self.load_embeddings(algorithm_version, strategy_version, dataset_version)
        if not full:
            return {}
        return {eid: vec for eid, vec in full.items() if eid in id_set}

    def save_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        *,
        strategy_file_path: Optional[Path] = None,
    ) -> None:
        strategy_hash = None
        if strategy_file_path and compute_strategy_hash:
            strategy_hash = compute_strategy_hash(strategy_file_path)
        if self._qdrant_available and self._qdrant:
            try:
                self._qdrant.save_embeddings(
                    algorithm_version, strategy_version, dataset_version,
                    embeddings, embedding_model, embedding_dimensions,
                    strategy_hash=strategy_hash,
                )
            except Exception as e:
                print(f"Qdrant save failed: {e}, saving to JSON only")
        self._cache.save_embeddings(
            algorithm_version, strategy_version, dataset_version,
            embeddings, embedding_model, embedding_dimensions,
        )

    def _migrate_to_qdrant(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        strategy_file_path: Optional[Path] = None,
    ) -> None:
        if not embeddings or not self._qdrant:
            return
        dimensions = len(next(iter(embeddings.values())))
        strategy_hash = None
        if strategy_file_path and compute_strategy_hash:
            strategy_hash = compute_strategy_hash(strategy_file_path)
        self._qdrant.save_embeddings(
            algorithm_version, strategy_version, dataset_version,
            embeddings, "migrated", dimensions,
            strategy_hash=strategy_hash,
        )
