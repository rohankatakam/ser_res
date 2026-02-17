"""
Similarity utilities — cosine similarity for semantic matching.
"""

from typing import List

import numpy as np


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    v1 = np.array(v1)
    v2 = np.array(v2)
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(dot_product / norm_product) if norm_product > 0 else 0.0
