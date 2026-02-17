"""Application state: loaders, stores, and current algorithm/dataset."""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .config import get_config, ServerConfig
    from .services import (
        AlgorithmLoader,
        DatasetLoader,
        DatasetEpisodeProvider,
        EmbeddingCache,
        FirestoreUserStore,
        JsonUserStore,
        LoadedAlgorithm,
        LoadedDataset,
        QdrantEmbeddingStore,
        QdrantJsonVectorStore,
        RequestOnlyEngagementStore,
        Validator,
    )
except ImportError:
    from config import get_config, ServerConfig
    from services import (
        AlgorithmLoader,
        DatasetLoader,
        DatasetEpisodeProvider,
        EmbeddingCache,
        FirestoreUserStore,
        JsonUserStore,
        LoadedAlgorithm,
        LoadedDataset,
        QdrantEmbeddingStore,
        QdrantJsonVectorStore,
        RequestOnlyEngagementStore,
        Validator,
    )


class AppState:
    """Global application state."""

    def __init__(self, config: ServerConfig):
        self.config = config

        # Loaders
        self.algorithm_loader = AlgorithmLoader(config.algorithms_dir)
        self.dataset_loader = DatasetLoader(config.datasets_dir)
        self.embedding_cache = EmbeddingCache(config.cache_dir / "embeddings")
        self.validator = Validator(self.algorithm_loader, self.dataset_loader)

        # Qdrant store (primary storage, with fallback to JSON cache)
        self.qdrant_store: Optional[QdrantEmbeddingStore] = None
        self.qdrant_available = False
        self._init_qdrant(config.qdrant_url)

        # Abstractions (swap implementations for cloud: Pinecone, Firestore)
        self.vector_store = QdrantJsonVectorStore(
            self.embedding_cache,
            self.qdrant_store if self.qdrant_available else None,
        )
        self.engagement_store = RequestOnlyEngagementStore()
        self.current_episode_provider: Optional[Any] = None
        self.user_store: Optional[Any] = self._create_user_store(config)

        # Currently loaded
        self.current_algorithm: Optional[LoadedAlgorithm] = None
        self.current_dataset: Optional[LoadedDataset] = None
        self.current_embeddings: Dict[str, List[float]] = {}

        # Session storage
        self.sessions: Dict[str, Dict] = {}

    def _create_user_store(self, config: ServerConfig) -> Optional[Any]:
        """Create user store from config (JSON or Firestore)."""
        cred_path = config.firebase_credentials_path
        cred_path_obj = Path(cred_path) if cred_path else None
        cred_exists = cred_path_obj and cred_path_obj.exists() if cred_path_obj else False
        cred_is_file = cred_path_obj and cred_path_obj.is_file() if cred_path_obj else False
        print(f"[startup] User store: DATA_SOURCE={config.data_source!r}, FIREBASE_CREDENTIALS_PATH={cred_path}, exists={cred_exists}, is_file={cred_is_file}")
        if config.data_source == "firebase" and config.firebase_credentials_path:
            if not cred_exists:
                print("[startup] Firestore user store skipped: credentials file not found. Set FIREBASE_CREDENTIALS_PATH in .env to your service account JSON path.")
                return None
            if not cred_is_file:
                print("[startup] Firestore user store skipped: FIREBASE_CREDENTIALS_PATH is a directory, not a file. Point it to your existing key file in .env.")
                return None
            try:
                return FirestoreUserStore(
                    project_id=config.firebase_project_id,
                    credentials_path=config.firebase_credentials_path,
                )
            except Exception as e:
                print(f"Firestore user store init failed: {e}, user persistence disabled")
                return None
        path = config.users_json_path or (config.cache_dir.parent / "data" / "users.json")
        try:
            return JsonUserStore(path)
        except Exception as e:
            print(f"JSON user store init failed: {e}, user persistence disabled")
            return None

    def _init_qdrant(self, qdrant_url: Optional[str]):
        """Initialize Qdrant connection with graceful fallback."""
        if qdrant_url:
            try:
                self.qdrant_store = QdrantEmbeddingStore(qdrant_url=qdrant_url)
                self.qdrant_available = self.qdrant_store.is_available
                if self.qdrant_available:
                    print(f"Qdrant connected at {qdrant_url}")
                else:
                    print(f"Qdrant not responding at {qdrant_url}, using JSON cache fallback")
            except Exception as e:
                print(f"Qdrant connection failed: {e}, using JSON cache fallback")
                self.qdrant_available = False
        else:
            print("No QDRANT_URL configured, using JSON cache only")

    @property
    def is_loaded(self) -> bool:
        return self.current_algorithm is not None and self.current_dataset is not None

    def has_embeddings_cached(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
    ) -> bool:
        """Check if embeddings are cached (delegates to vector_store)."""
        return self.vector_store.has_cache(
            algorithm_folder, strategy_version, dataset_folder
        )

    def load_cached_embeddings(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
        strategy_file_path: Optional[Path] = None,
    ) -> Optional[Dict[str, List[float]]]:
        """Load embeddings from vector_store (Qdrant + JSON today; Pinecone when swapped)."""
        emb = self.vector_store.load_embeddings(
            algorithm_folder,
            strategy_version,
            dataset_folder,
            strategy_file_path=strategy_file_path,
        )
        if emb:
            print(f"Loaded {len(emb)} embeddings from vector store")
        return emb

    def save_embeddings(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        strategy_file_path: Optional[Path] = None,
    ):
        """Save embeddings via vector_store (Qdrant + JSON today; Pinecone when swapped)."""
        self.vector_store.save_embeddings(
            algorithm_folder,
            strategy_version,
            dataset_folder,
            embeddings,
            embedding_model,
            embedding_dimensions,
            strategy_file_path=strategy_file_path,
        )


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        config = get_config()
        _state = AppState(config)
    return _state
