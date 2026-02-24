"""
Vector Store abstraction.

Only Pinecone is supported for embeddings. PINECONE_API_KEY is required at startup.
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from .pinecone_store import PineconeEmbeddingStore


class VectorStore(Protocol):
    """Protocol for embedding storage. Only Pinecone is supported."""

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
        metadata_by_id: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """Persist embeddings. Optionally include metadata per episode for Pinecone filtering."""
        ...


class PineconeVectorStore:
    """
    Vector store adapter that wraps PineconeEmbeddingStore and implements VectorStore.
    Used when PINECONE_API_KEY is set. load_embeddings returns None (no full in-memory load);
    get_embeddings fetches by id from Pinecone.
    """

    def __init__(self, pinecone_store: PineconeEmbeddingStore):
        if pinecone_store is None:
            raise ValueError("pinecone_store is required")
        self._store = pinecone_store

    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> bool:
        return self._store.has_cache(
            algorithm_version, strategy_version, dataset_version
        )

    def get_vector_count(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> int:
        """Return the number of vectors in Pinecone for this namespace (for stats)."""
        return getattr(
            self._store,
            "get_vector_count",
            lambda *a, **k: 0,
        )(algorithm_version, strategy_version, dataset_version)

    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        *,
        strategy_file_path: Optional[Path] = None,
    ) -> Optional[Dict[str, List[float]]]:
        """Pinecone does not load all vectors into memory; return None so callers use get_embeddings(ids)."""
        return None

    def get_embeddings(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        return self._store.get_embeddings(
            episode_ids, algorithm_version, strategy_version, dataset_version
        )

    async def get_embeddings_async(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        """Async fetch. Requires store to implement get_embeddings_async (Pinecone with asyncio)."""
        return await self._store.get_embeddings_async(
            episode_ids, algorithm_version, strategy_version, dataset_version
        )

    async def query_async(
        self,
        vector: List[float],
        top_k: int,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        filter: Optional[dict] = None,
    ) -> List[Tuple[str, float]]:
        """Query approximate NN. Returns [(episode_id, score), ...]. Requires Pinecone store."""
        return await self._store.query_async(
            vector, top_k, algorithm_version, strategy_version, dataset_version, filter
        )

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
        metadata_by_id: Optional[Dict[str, Dict]] = None,
    ) -> None:
        self._store.save_embeddings(
            algorithm_version,
            strategy_version,
            dataset_version,
            embeddings,
            embedding_model,
            embedding_dimensions,
            metadata_by_id=metadata_by_id,
        )
