"""
Qdrant Embedding Store

Stores and retrieves episode embeddings using Qdrant vector database.
Provides the same interface as EmbeddingCache for backward compatibility,
with additional vector search capabilities.

Collection naming: {algorithm_version}_s{strategy_version}__{dataset_version}
Example: v1_5_diversified_s1_0__eval_909_feb2026

Includes hash-based change detection for embedding strategy files.
"""

import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.exceptions import UnexpectedResponse
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    QdrantClient = None
    models = None


@dataclass
class QdrantCacheMetadata:
    """Metadata about embeddings stored in Qdrant."""
    algorithm_version: str
    strategy_version: str
    dataset_version: str
    embedding_model: str
    embedding_dimensions: int
    created_at: str
    episode_count: int
    collection_name: str
    strategy_hash: Optional[str] = None  # SHA256 hash of embedding/embedding_strategy.py


def compute_strategy_hash(strategy_file_path: Path) -> Optional[str]:
    """
    Compute SHA256 hash of embedding strategy file.
    
    Args:
        strategy_file_path: Path to embedding/embedding_strategy.py
    
    Returns:
        SHA256 hex digest, or None if file not found
    """
    try:
        with open(strategy_file_path, 'rb') as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()[:16]  # First 16 chars for brevity
    except (IOError, FileNotFoundError):
        return None


class QdrantEmbeddingStore:
    """
    Manages episode embeddings in Qdrant vector database.
    
    Provides the same interface as EmbeddingCache for easy swapping,
    with additional vector similarity search capabilities.
    
    Usage:
        store = QdrantEmbeddingStore(qdrant_url="http://localhost:6333")
        
        # Check if embeddings exist
        if store.has_cache("v1_5_diversified", "1.0", "eval_909_feb2026"):
            embeddings = store.load_embeddings(...)
        else:
            # Generate and save
            store.save_embeddings(..., embeddings)
        
        # Vector similarity search (Qdrant-specific)
        results = store.search_similar(user_vector, limit=100)
    """
    
    # Retry configuration for connection issues
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the Qdrant embedding store.
        
        Args:
            qdrant_url: Qdrant server URL (falls back to QDRANT_URL env var)
            timeout: Connection timeout in seconds
        """
        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        self.timeout = timeout
        self._client: Optional[QdrantClient] = None
        self._current_collection: Optional[str] = None
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client with connection retry."""
        if not HAS_QDRANT:
            raise ImportError(
                "qdrant-client package not installed. Install with: pip install qdrant-client"
            )
        
        if self._client is None:
            for attempt in range(self.MAX_RETRIES):
                try:
                    self._client = QdrantClient(
                        url=self.qdrant_url,
                        timeout=self.timeout
                    )
                    # Test connection
                    self._client.get_collections()
                    break
                except Exception as e:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                    else:
                        raise ConnectionError(
                            f"Failed to connect to Qdrant at {self.qdrant_url}: {e}"
                        )
        
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if Qdrant is available and connected."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
    
    def get_collection_name(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> str:
        """
        Generate collection name for an algorithm+dataset combination.
        
        Names are sanitized for Qdrant's collection naming rules.
        """
        # Sanitize versions for collection name (alphanumeric and underscores only)
        algo = algorithm_version.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")
        strat = strategy_version.replace(".", "_")
        data = dataset_version.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")
        return f"{algo}_s{strat}__{data}"
    
    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> bool:
        """Check if embeddings are cached for this combination."""
        try:
            collection_name = self.get_collection_name(
                algorithm_version, strategy_version, dataset_version
            )
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False
    
    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> Optional[Dict[str, List[float]]]:
        """
        Load all embeddings from Qdrant collection.
        
        Returns:
            Dict mapping episode_id to embedding vector, or None if not cached
        """
        collection_name = self.get_collection_name(
            algorithm_version, strategy_version, dataset_version
        )
        
        if not self.has_cache(algorithm_version, strategy_version, dataset_version):
            return None
        
        try:
            # Get collection info to know total points
            collection_info = self.client.get_collection(collection_name)
            total_points = collection_info.points_count
            
            if total_points == 0:
                return {}
            
            # Scroll through all points (paginated)
            embeddings = {}
            offset = None
            batch_size = 100
            
            while True:
                results = self.client.scroll(
                    collection_name=collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )
                
                points, next_offset = results
                
                for point in points:
                    episode_id = point.payload.get("episode_id", str(point.id))
                    embeddings[episode_id] = point.vector
                
                if next_offset is None:
                    break
                offset = next_offset
            
            self._current_collection = collection_name
            return embeddings
            
        except Exception as e:
            print(f"Warning: Failed to load embeddings from Qdrant: {e}")
            return None
    
    def load_metadata(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> Optional[QdrantCacheMetadata]:
        """
        Load metadata about cached embeddings.
        
        Returns:
            QdrantCacheMetadata or None if not cached
        """
        collection_name = self.get_collection_name(
            algorithm_version, strategy_version, dataset_version
        )
        
        if not self.has_cache(algorithm_version, strategy_version, dataset_version):
            return None
        
        try:
            collection_info = self.client.get_collection(collection_name)
            
            # Get strategy_hash from first point's payload
            strategy_hash = None
            created_at = ""
            try:
                results = self.client.scroll(
                    collection_name=collection_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )
                points, _ = results
                if points:
                    strategy_hash = points[0].payload.get("strategy_hash")
                    created_at = points[0].payload.get("created_at", "")
            except Exception:
                pass
            
            return QdrantCacheMetadata(
                algorithm_version=algorithm_version,
                strategy_version=strategy_version,
                dataset_version=dataset_version,
                embedding_model=collection_info.config.params.vectors.distance.name if hasattr(collection_info.config.params.vectors, 'distance') else "unknown",
                embedding_dimensions=collection_info.config.params.vectors.size if hasattr(collection_info.config.params.vectors, 'size') else 0,
                created_at=created_at,
                episode_count=collection_info.points_count,
                collection_name=collection_name,
                strategy_hash=strategy_hash
            )
        except Exception:
            return None
    
    def verify_strategy_hash(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        current_hash: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that stored embeddings match the current embedding strategy.
        
        Args:
            algorithm_version: Algorithm version
            strategy_version: Strategy version
            dataset_version: Dataset version
            current_hash: Current SHA256 hash of embedding/embedding_strategy.py
        
        Returns:
            (matches, stored_hash) - True if hashes match or no stored hash
        """
        metadata = self.load_metadata(algorithm_version, strategy_version, dataset_version)
        
        if not metadata:
            return True, None  # No cache, nothing to verify
        
        stored_hash = metadata.strategy_hash
        
        if stored_hash is None:
            return True, None  # No stored hash (legacy cache), assume OK
        
        return current_hash == stored_hash, stored_hash
    
    def save_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        strategy_hash: Optional[str] = None
    ) -> str:
        """
        Save embeddings to Qdrant collection.
        
        Args:
            algorithm_version: Version of the algorithm
            strategy_version: Version of the embedding strategy
            dataset_version: Version of the dataset
            embeddings: Dict mapping episode_id to embedding vector
            embedding_model: Name of the embedding model used
            embedding_dimensions: Dimensionality of embeddings
            strategy_hash: SHA256 hash of embedding/embedding_strategy.py (for change detection)
        
        Returns:
            Collection name that was created/updated
        """
        collection_name = self.get_collection_name(
            algorithm_version, strategy_version, dataset_version
        )
        
        # Delete existing collection if it exists
        if self.has_cache(algorithm_version, strategy_version, dataset_version):
            self.client.delete_collection(collection_name)
        
        # Create collection with correct dimensions
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_dimensions,
                distance=models.Distance.COSINE
            )
        )
        
        created_at = datetime.now().isoformat()
        
        # Upload embeddings in batches
        batch_size = 100
        episode_ids = list(embeddings.keys())
        
        for i in range(0, len(episode_ids), batch_size):
            batch_ids = episode_ids[i:i + batch_size]
            
            points = []
            for idx, episode_id in enumerate(batch_ids):
                points.append(models.PointStruct(
                    id=i + idx,  # Numeric ID for Qdrant
                    vector=embeddings[episode_id],
                    payload={
                        "episode_id": episode_id,
                        "algorithm_version": algorithm_version,
                        "strategy_version": strategy_version,
                        "dataset_version": dataset_version,
                        "embedding_model": embedding_model,
                        "strategy_hash": strategy_hash,
                        "created_at": created_at
                    }
                ))
            
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
        
        self._current_collection = collection_name
        print(f"Saved {len(embeddings)} embeddings to Qdrant collection '{collection_name}'")
        if strategy_hash:
            print(f"Strategy hash: {strategy_hash}")
        return collection_name
    
    def delete_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str
    ) -> bool:
        """
        Delete cached embeddings collection.
        
        Returns:
            True if collection was deleted, False if it didn't exist
        """
        collection_name = self.get_collection_name(
            algorithm_version, strategy_version, dataset_version
        )
        
        if self.has_cache(algorithm_version, strategy_version, dataset_version):
            self.client.delete_collection(collection_name)
            return True
        return False
    
    def list_cached(self) -> List[QdrantCacheMetadata]:
        """
        List all cached embedding collections.
        
        Returns:
            List of QdrantCacheMetadata for each collection
        """
        try:
            collections = self.client.get_collections().collections
            results = []
            
            for coll in collections:
                # Parse collection name to extract versions
                # Format: {algo}_s{strat}__{dataset}
                name = coll.name
                try:
                    if "__" in name and "_s" in name:
                        algo_strat, dataset = name.split("__", 1)
                        algo, strat = algo_strat.rsplit("_s", 1)
                        
                        info = self.client.get_collection(name)
                        results.append(QdrantCacheMetadata(
                            algorithm_version=algo,
                            strategy_version=strat.replace("_", "."),
                            dataset_version=dataset,
                            embedding_model="",
                            embedding_dimensions=info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else 0,
                            created_at="",
                            episode_count=info.points_count,
                            collection_name=name
                        ))
                except Exception:
                    continue
            
            return results
        except Exception:
            return []
    
    def search_similar(
        self,
        query_vector: List[float],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        limit: int = 100,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Search for similar episodes using vector similarity.
        
        This is a Qdrant-specific method that leverages native vector search
        for O(log n) performance vs O(n) manual search.
        
        Args:
            query_vector: The user embedding vector to search with
            algorithm_version: Algorithm version for collection lookup
            strategy_version: Strategy version
            dataset_version: Dataset version
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1 for cosine)
        
        Returns:
            List of (episode_id, similarity_score) tuples, sorted by score descending
        """
        collection_name = self.get_collection_name(
            algorithm_version, strategy_version, dataset_version
        )
        
        if not self.has_cache(algorithm_version, strategy_version, dataset_version):
            return []
        
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            return [
                (hit.payload.get("episode_id", str(hit.id)), hit.score)
                for hit in results
            ]
        except Exception as e:
            print(f"Warning: Qdrant search failed: {e}")
            return []


def check_qdrant_available(qdrant_url: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if Qdrant is available and connected.
    
    Returns:
        (is_available, message)
    """
    if not HAS_QDRANT:
        return False, "qdrant-client package not installed"
    
    url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
    
    try:
        store = QdrantEmbeddingStore(qdrant_url=url)
        if store.is_available:
            return True, f"Qdrant connected at {url}"
        else:
            return False, f"Qdrant not responding at {url}"
    except Exception as e:
        return False, f"Qdrant connection failed: {e}"
