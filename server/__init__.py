"""
Serafis Evaluation Framework Server

Usage: uvicorn server:app --reload --port 8000
"""

from .app import app
from .config import ServerConfig, get_config, reload_config
from .services import (
    AlgorithmLoader,
    CompatibilityResult,
    DatasetLoader,
    EmbeddingCache,
    EmbeddingGenerator,
    Validator,
)

__all__ = [
    "app",
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
