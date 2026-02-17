"""
Serafis Evaluation Framework Server

This package provides the core infrastructure for the evaluation framework:
- EmbeddingCache: Manages cached embeddings keyed by algorithm+dataset combo
- EmbeddingGenerator: Generates embeddings using OpenAI API
- AlgorithmLoader: Dynamically loads algorithm versions
- DatasetLoader: Dynamically loads datasets
- Validator: Checks algorithm-dataset compatibility
- ServerConfig: Configuration management
"""

from .config import ServerConfig, get_config, reload_config
from .embedding_cache import EmbeddingCache
from .embedding_generator import EmbeddingGenerator
from .algorithm_loader import AlgorithmLoader
from .dataset_loader import DatasetLoader
from .validator import Validator, CompatibilityResult

__all__ = [
    "ServerConfig",
    "get_config",
    "reload_config",
    "EmbeddingCache",
    "EmbeddingGenerator",
    "AlgorithmLoader",
    "DatasetLoader",
    "Validator",
    "CompatibilityResult",
]
