"""Config and algorithm config Pydantic models."""

from pydantic import BaseModel


class LoadConfigRequest(BaseModel):
    algorithm: str
    dataset: str
    generate_embeddings: bool = True
