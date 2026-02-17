"""Embeddings-related Pydantic models."""

from pydantic import BaseModel


class GenerateEmbeddingsRequest(BaseModel):
    algorithm: str
    dataset: str
    force: bool = False
