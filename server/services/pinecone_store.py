"""
Pinecone embedding store for episode vectors.

Requires pinecone[asyncio] (pip install 'pinecone[asyncio]'). Sync methods are kept
for scripts (e.g. populate_pinecone); session create uses async only.
Uses namespaces per algorithm_version + strategy_version + dataset_version.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

try:
    from pinecone import Pinecone, ServerlessSpec
    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False
    Pinecone = None
    ServerlessSpec = None

PINECONE_ASYNC_REQUIRED_MSG = (
    "Pinecone asyncio support is required. Install with: pip install 'pinecone[asyncio]'"
)

# Default dimension for OpenAI text-embedding-3-small
DEFAULT_DIMENSION = 1536


def _sanitize(s: str) -> str:
    """Sanitize for Pinecone namespace: no spaces, limited chars."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", (s or "").replace(".", "_")) or "default"


def _namespace(
    algorithm_version: str,
    strategy_version: str,
    dataset_version: str,
) -> str:
    """Namespace for this algo+strategy+dataset (same pattern as Qdrant collection)."""
    a = _sanitize(algorithm_version)
    s = _sanitize(strategy_version)
    d = _sanitize(dataset_version)
    return f"{a}_s{s}__{d}"


class PineconeEmbeddingStore:
    """
    Episode embeddings in Pinecone, keyed by episode id for Firestore lookup.

    Uses PINECONE_API_KEY from env. Index name from PINECONE_INDEX_NAME or default.
    """

    DEFAULT_INDEX_NAME = "serafis-episodes"

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        dimension: int = DEFAULT_DIMENSION,
        cloud: str = "aws",
        region: str = "us-east-1",
    ):
        if not HAS_PINECONE:
            raise ImportError("pinecone package required. pip install pinecone")
        self._api_key = (api_key or os.environ.get("PINECONE_API_KEY") or "").strip()
        if not self._api_key:
            raise ValueError("PINECONE_API_KEY is required for PineconeEmbeddingStore")
        self._index_name = (index_name or os.environ.get("PINECONE_INDEX_NAME") or self.DEFAULT_INDEX_NAME).strip()
        self._dimension = dimension
        self._cloud = cloud
        self._region = region
        self._client: Optional[Pinecone] = None
        self._index = None
        self._index_host: Optional[str] = None

    def _get_index_host(self) -> str:
        """Resolve index host for async fetch (cached). Required for get_embeddings_async."""
        if self._index_host is not None:
            return self._index_host
        print(f"[Pinecone] resolving index host for {self._index_name!r}...", flush=True)
        try:
            desc = self.client.describe_index(self._index_name)
            host = getattr(desc, "host", None) or (
                desc.get("host") if isinstance(desc, dict) else None
            )
            if not host:
                raise ValueError(
                    f"Pinecone index {self._index_name!r} has no host; check index exists and API key."
                )
            self._index_host = host
            print(f"[Pinecone] index host resolved: {host!r}", flush=True)
            return self._index_host
        except Exception as e:
            print(f"[Pinecone] _get_index_host failed: {e}", flush=True)
            raise RuntimeError(
                f"Could not resolve Pinecone index host for {self._index_name!r}: {e}"
            ) from e

    @property
    def client(self) -> Pinecone:
        if self._client is None:
            self._client = Pinecone(api_key=self._api_key)
        return self._client

    @property
    def index(self):
        if self._index is None:
            if not self.client.has_index(self._index_name):
                self.client.create_index(
                    name=self._index_name,
                    dimension=self._dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud=self._cloud, region=self._region),
                )
            self._index = self.client.Index(self._index_name)
        return self._index

    def _ns(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> str:
        return _namespace(algorithm_version, strategy_version, dataset_version)

    @property
    def is_available(self) -> bool:
        try:
            self.client.list_indexes()
            return True
        except Exception:
            return False

    def has_cache(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> bool:
        try:
            ns = self._ns(algorithm_version, strategy_version, dataset_version)
            stats = self.index.describe_index_stats()
            if stats.namespaces and ns in stats.namespaces:
                return (stats.namespaces[ns].vector_count or 0) > 0
            return False
        except Exception:
            return False

    def get_vector_count(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> int:
        """Return the number of vectors in the namespace for this algo/strategy/dataset."""
        try:
            ns = self._ns(algorithm_version, strategy_version, dataset_version)
            stats = self.index.describe_index_stats()
            count = 0
            if stats.namespaces and ns in stats.namespaces:
                count = stats.namespaces[ns].vector_count or 0
            print(f"[Pinecone] get_vector_count namespace={ns!r} -> {count}")
            return count
        except Exception as e:
            print(f"[Pinecone] get_vector_count failed: {e}")
            return 0

    def get_embeddings(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        """
        Fetch vectors by episode id (same id as Firestore). Returns dict episode_id -> vector.
        """
        if not episode_ids:
            return {}
        try:
            ns = self._ns(algorithm_version, strategy_version, dataset_version)
            # Pinecone fetch: ids must be strings
            result = self.index.fetch(ids=episode_ids, namespace=ns)
            out: Dict[str, List[float]] = {}
            if result.vectors:
                for eid, record in result.vectors.items():
                    if record:
                        vals = record.get("values") if isinstance(record, dict) else getattr(record, "values", None)
                        if vals is not None:
                            out[eid] = list(vals)
            print(f"[Pinecone] get_embeddings namespace={ns!r} requested={len(episode_ids)} returned={len(out)}")
            return out
        except Exception as e:
            print(f"[Pinecone] get_embeddings failed: {e}")
            return {}

    async def get_embeddings_async(
        self,
        episode_ids: List[str],
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Dict[str, List[float]]:
        """Async fetch via IndexAsyncio (SDK: sync Pinecone + pc.IndexAsyncio(host) per call). Requires pinecone[asyncio]."""
        if not episode_ids:
            return {}
        print(f"[Pinecone] get_embeddings_async started ids={len(episode_ids)}", flush=True)
        host = self._get_index_host()
        ns = self._ns(algorithm_version, strategy_version, dataset_version)
        pc = self.client
        try:
            print(f"[Pinecone] get_embeddings_async fetching namespace={ns!r}...", flush=True)
            async with pc.IndexAsyncio(host=host) as idx:
                fetched = await idx.fetch(ids=episode_ids, namespace=ns)
            print(f"[Pinecone] get_embeddings_async fetch done", flush=True)
        except Exception as e:
            print(f"[Pinecone] get_embeddings_async failed: {type(e).__name__}: {e}", flush=True)
            err_msg = str(e).lower()
            if "asyncio" in err_msg or "additional dependencies" in err_msg:
                raise ImportError(PINECONE_ASYNC_REQUIRED_MSG) from e
            raise
        out: Dict[str, List[float]] = {}
        if fetched.vectors:
            for eid, record in fetched.vectors.items():
                if record:
                    vals = getattr(record, "values", None)
                    if vals is not None:
                        out[eid] = list(vals)
        print(f"[Pinecone] get_embeddings_async namespace={ns!r} requested={len(episode_ids)} returned={len(out)}")
        return out

    async def query_async(
        self,
        vector: List[float],
        top_k: int,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        filter: Optional[dict] = None,
    ) -> List[Tuple[str, float]]:
        """
        Query approximate NN by vector. Returns [(episode_id, score), ...].
        Uses include_values=False, include_metadata=False for latency.
        """
        if not vector:
            return []
        host = self._get_index_host()
        ns = self._ns(algorithm_version, strategy_version, dataset_version)
        pc = self.client
        try:
            print(f"[Pinecone] query_async started top_k={top_k} namespace={ns!r}", flush=True)
            async with pc.IndexAsyncio(host=host) as idx:
                result = await idx.query(
                    vector=vector,
                    top_k=top_k,
                    namespace=ns,
                    filter=filter,
                    include_values=False,
                    include_metadata=False,
                )
            matches = result.matches if hasattr(result, "matches") and result.matches else []
            out = []
            for m in matches:
                mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None)
                mscore = getattr(m, "score", None)
                if mscore is None and isinstance(m, dict):
                    mscore = m.get("score")
                if mid and mscore is not None:
                    out.append((str(mid), float(mscore)))
            print(f"[Pinecone] query_async done namespace={ns!r} returned={len(out)}")
            return out
        except Exception as e:
            print(f"[Pinecone] query_async failed: {type(e).__name__}: {e}", flush=True)
            err_msg = str(e).lower()
            if "asyncio" in err_msg or "additional dependencies" in err_msg:
                raise ImportError(PINECONE_ASYNC_REQUIRED_MSG) from e
            raise

    def save_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        strategy_hash: Optional[str] = None,
    ) -> None:
        """Upsert embeddings with episode id as vector id for later lookup."""
        if not embeddings:
            return
        ns = self._ns(algorithm_version, strategy_version, dataset_version)
        vectors = []
        for episode_id, values in embeddings.items():
            vectors.append({
                "id": episode_id,
                "values": values,
            })
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=ns)
        print(f"Upserted {len(embeddings)} embeddings to Pinecone index '{self._index_name}' namespace '{ns}'")

    def load_embeddings(
        self,
        algorithm_version: str,
        strategy_version: str,
        dataset_version: str,
    ) -> Optional[Dict[str, List[float]]]:
        """
        Load all vectors from the namespace (for small catalogs or migration).
        For production prefer get_embeddings(ids) to avoid loading everything.
        """
        try:
            ns = self._ns(algorithm_version, strategy_version, dataset_version)
            # List by querying with a zero vector and high top_k, or use list pagination
            # Pinecone doesn't have "list all"; we'd need to query. For now return None
            # so callers use get_embeddings(ids) instead.
            return None
        except Exception:
            return None
