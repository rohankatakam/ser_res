"""Backing logic: loaders, stores, abstractions."""

from .algorithm_loader import AlgorithmLoader, LoadedAlgorithm
from .dataset_loader import DatasetLoader, LoadedDataset
from .embedding_generator import EmbeddingGenerator, EmbeddingProgress, check_openai_available
from .validator import Validator, CompatibilityResult
from .pinecone_store import PineconeEmbeddingStore
from .vector_store import PineconeVectorStore, VectorStore
from .episode_provider import (
    DatasetEpisodeProvider,
    EpisodeProvider,
    FirestoreEpisodeProvider,
    JsonEpisodeProvider,
)
from .engagement_store import EngagementStore, RequestOnlyEngagementStore
from .firestore_engagement_store import FirestoreEngagementStore
from .user_store import FirestoreUserStore, JsonUserStore, UserStore

__all__ = [
    "AlgorithmLoader",
    "LoadedAlgorithm",
    "DatasetLoader",
    "LoadedDataset",
    "EmbeddingGenerator",
    "EmbeddingProgress",
    "check_openai_available",
    "Validator",
    "CompatibilityResult",
    "PineconeEmbeddingStore",
    "PineconeVectorStore",
    "VectorStore",
    "DatasetEpisodeProvider",
    "EpisodeProvider",
    "FirestoreEpisodeProvider",
    "FirestoreUserStore",
    "JsonEpisodeProvider",
    "JsonUserStore",
    "UserStore",
    "EngagementStore",
    "FirestoreEngagementStore",
    "RequestOnlyEngagementStore",
]
