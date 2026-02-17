"""Embedding strategy: get_embed_text and model constants."""

from .embedding_strategy import (
    get_embed_text,
    STRATEGY_VERSION,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    validate_episode_for_embedding,
)

__all__ = [
    "get_embed_text",
    "STRATEGY_VERSION",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "validate_episode_for_embedding",
]
