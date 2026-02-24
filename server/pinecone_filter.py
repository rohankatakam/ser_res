"""Build Pinecone metadata filter for query path (quality, freshness, exclusions)."""

import time
from typing import Optional, Set

# Pinecone $nin accepts max 10,000 values
MAX_NIN_VALUES = 10_000


def build_pinecone_filter(
    config,
    excluded_ids: Set[str],
) -> Optional[dict]:
    """
    Build Pinecone metadata filter from config and excluded_ids.
    Vectors must have metadata: credibility, combined, published_at, episode_id.
    Returns None if config is None or filter cannot be built.
    """
    if config is None:
        return None
    credibility_floor = getattr(config, "credibility_floor", 2)
    combined_floor = getattr(config, "combined_floor", 5)
    freshness_window_days = getattr(config, "freshness_window_days", 90)

    cutoff = int(time.time()) - (freshness_window_days * 86400)
    clauses = [
        {"credibility": {"$gte": credibility_floor}},
        {"combined": {"$gte": combined_floor}},
        {"published_at": {"$gte": cutoff}},
    ]
    if excluded_ids:
        excluded_list = list(excluded_ids)[:MAX_NIN_VALUES]
        clauses.append({"episode_id": {"$nin": excluded_list}})

    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
