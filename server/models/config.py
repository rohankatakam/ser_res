"""Config and algorithm config Pydantic models."""

from typing import Any, Dict

from pydantic import BaseModel


class LoadConfigRequest(BaseModel):
    algorithm: str
    dataset: str
    generate_embeddings: bool = True


class ConfigUpdateRequest(BaseModel):
    """Request body for config update."""
    config: Dict[str, Any]


class ComputeParamsRequest(BaseModel):
    """Request body for computing derived parameters."""
    base_params: Dict[str, Any]
    profile: Dict[str, Any] | None = None
