"""Application state: loaders, stores, and current algorithm/dataset."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .config import get_config, ServerConfig
    from .services import (
        AlgorithmLoader,
        DatasetLoader,
        DatasetEpisodeProvider,
        FirestoreEngagementStore,
        FirestoreUserStore,
        LoadedAlgorithm,
        LoadedDataset,
        PineconeEmbeddingStore,
        PineconeVectorStore,
        RequestOnlyEngagementStore,
        Validator,
    )
except ImportError:
    from config import get_config, ServerConfig
    from services import (
        AlgorithmLoader,
        DatasetLoader,
        DatasetEpisodeProvider,
        FirestoreEngagementStore,
        FirestoreUserStore,
        LoadedAlgorithm,
        LoadedDataset,
        PineconeEmbeddingStore,
        PineconeVectorStore,
        RequestOnlyEngagementStore,
        Validator,
    )


class AppState:
    """Global application state."""

    def __init__(self, config: ServerConfig):
        self.config = config

        # Loaders
        self.algorithm_loader = AlgorithmLoader(config.algorithms_dir)
        self.dataset_loader = DatasetLoader(config.fixtures_dir)
        self.validator = Validator(self.algorithm_loader, self.dataset_loader)

        # Vector store: Pinecone only (separate index for rec_for_you, not shared with RAG).
        pinecone_key = (os.environ.get("PINECONE_API_KEY") or "").strip()
        if not pinecone_key:
            raise ValueError(
                "PINECONE_API_KEY is required. Set it in .env for embeddings (Pinecone)."
            )
        index_name = getattr(
            config, "pinecone_rec_for_you_index", None
        ) or os.environ.get("PINECONE_REC_FOR_YOU_INDEX", "rec-for-you")
        pinecone_store = PineconeEmbeddingStore(api_key=pinecone_key, index_name=index_name)
        self.vector_store = PineconeVectorStore(pinecone_store)
        print("[startup] Vector store: Pinecone")

        # Engagement store: Firestore when creds set, else request-only
        self.engagement_store = self._create_engagement_store(config)
        _es = type(self.engagement_store).__name__
        print(f"[startup] Engagement store: {_es}")
        self.current_episode_provider: Optional[Any] = None
        self.user_store: Optional[Any] = self._create_user_store(config)

        # Currently loaded
        self.current_algorithm: Optional[LoadedAlgorithm] = None
        self.current_dataset: Optional[LoadedDataset] = None
        self.current_embeddings: Dict[str, List[float]] = {}

        # Session storage
        self.sessions: Dict[str, Dict] = {}

    def _create_engagement_store(self, config: ServerConfig) -> Any:
        """Create engagement store (Firestore when creds set, else request-only)."""
        if config.firebase_credentials_path:
            cred_path = Path(config.firebase_credentials_path)
            if not cred_path.exists() or not cred_path.is_file():
                print(
                    f"[startup] Firestore engagement store skipped: credentials path not found or not a file: {cred_path}"
                )
            else:
                try:
                    return FirestoreEngagementStore(
                        project_id=config.firebase_project_id,
                        credentials_path=config.firebase_credentials_path,
                    )
                except Exception as e:
                    print(f"[startup] Firestore engagement store init failed: {e}, using request-only")
        return RequestOnlyEngagementStore()

    def _create_user_store(self, config: ServerConfig) -> Optional[Any]:
        """Create user store from config (JSON or Firestore)."""
        cred_path = config.firebase_credentials_path
        cred_path_obj = Path(cred_path) if cred_path else None
        cred_exists = cred_path_obj and cred_path_obj.exists() if cred_path_obj else False
        cred_is_file = cred_path_obj and cred_path_obj.is_file() if cred_path_obj else False
        print(f"[startup] User store: FIREBASE_CREDENTIALS_PATH={cred_path}, exists={cred_exists}, is_file={cred_is_file}")
        if config.firebase_credentials_path:
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
        return None

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
        """Load embeddings from vector_store (Pinecone; returns None so callers use get_embeddings by id)."""
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
        metadata_by_id: Optional[Dict[str, Dict]] = None,
    ):
        """Save embeddings via vector_store (Pinecone only). Optionally include metadata for filtering."""
        self.vector_store.save_embeddings(
            algorithm_folder,
            strategy_version,
            dataset_folder,
            embeddings,
            embedding_model,
            embedding_dimensions,
            strategy_file_path=strategy_file_path,
            metadata_by_id=metadata_by_id,
        )


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        config = get_config()
        _state = AppState(config)
    return _state
