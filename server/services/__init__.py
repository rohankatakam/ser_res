"""Backing logic: loaders, stores, abstractions."""

from .algorithm_loader import AlgorithmLoader, LoadedAlgorithm
from .dataset_loader import DatasetLoader, LoadedDataset
from .embedding_cache import EmbeddingCache
from .embedding_generator import EmbeddingGenerator, EmbeddingProgress, check_openai_available
from .validator import Validator, CompatibilityResult
from .qdrant_store import (
    QdrantEmbeddingStore,
    check_qdrant_available,
    compute_strategy_hash,
)
from .vector_store import QdrantJsonVectorStore, VectorStore
from .episode_provider import DatasetEpisodeProvider, EpisodeProvider
from .engagement_store import EngagementStore, RequestOnlyEngagementStore

__all__ = [
    "AlgorithmLoader",
    "LoadedAlgorithm",
    "DatasetLoader",
    "LoadedDataset",
    "EmbeddingCache",
    "EmbeddingGenerator",
    "EmbeddingProgress",
    "check_openai_available",
    "Validator",
    "CompatibilityResult",
    "QdrantEmbeddingStore",
    "check_qdrant_available",
    "compute_strategy_hash",
    "QdrantJsonVectorStore",
    "VectorStore",
    "DatasetEpisodeProvider",
    "EpisodeProvider",
    "EngagementStore",
    "RequestOnlyEngagementStore",
]
