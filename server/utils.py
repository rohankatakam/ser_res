"""Pure helpers: config merge, schema validation, episode card formatting."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

# Session/recommendation constants (used by routes/sessions)
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20

try:
    from .models import EpisodeCard, EpisodeScores, SeriesInfo
except ImportError:
    from models import EpisodeCard, EpisodeScores, SeriesInfo


def _metadata_for_episode(ep: dict) -> dict:
    """Build Pinecone metadata for an episode (credibility, insight, combined, published_at, episode_id)."""
    scores = ep.get("scores") or {}
    credibility = int(scores.get("credibility") or 0)
    insight = int(scores.get("insight") or 0)
    combined = credibility + insight
    published_at = 0
    pub_str = ep.get("published_at") or ""
    if pub_str:
        try:
            dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            published_at = int(dt.timestamp())
        except Exception:
            pass
    eid = ep.get("id") or ep.get("content_id") or ""
    return {
        "credibility": credibility,
        "insight": insight,
        "combined": combined,
        "published_at": published_at,
        "episode_id": eid,
    }


def build_metadata_by_id(episodes: List[dict], embedding_ids: Set[str]) -> Dict[str, dict]:
    """Build metadata_by_id for Pinecone upsert from episodes and embedding IDs."""
    ep_by_id = {ep.get("id") or ep.get("content_id"): ep for ep in episodes if ep.get("id") or ep.get("content_id")}
    return {
        eid: _metadata_for_episode(ep_by_id[eid])
        for eid in embedding_ids
        if eid in ep_by_id
    }


def deep_merge(base: dict, updates: dict) -> dict:
    """Deep merge updates into base dict, returning new dict."""
    result = base.copy()
    for key, value in updates.items():
        if key.startswith("_"):
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config_against_schema(config: dict, schema: dict) -> list:
    """
    Validate config values against schema constraints.
    Returns list of validation errors (empty if valid).
    """
    errors = []

    for group in schema.get("groups", []):
        for param in group.get("params", []):
            key_path = param["key"]
            parts = key_path.split(".")

            value = config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break

            if value is None:
                continue

            param_type = param.get("type", "float")
            min_val = param.get("min")
            max_val = param.get("max")

            if param_type == "int":
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"{key_path}: expected int, got {type(value).__name__}")
                elif min_val is not None and value < min_val:
                    errors.append(f"{key_path}: {value} is below minimum {min_val}")
                elif max_val is not None and value > max_val:
                    errors.append(f"{key_path}: {value} exceeds maximum {max_val}")

            elif param_type == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"{key_path}: expected float, got {type(value).__name__}")
                elif min_val is not None and value < min_val:
                    errors.append(f"{key_path}: {value} is below minimum {min_val}")
                elif max_val is not None and value > max_val:
                    errors.append(f"{key_path}: {value} exceeds maximum {max_val}")

            elif param_type == "boolean":
                if not isinstance(value, bool):
                    errors.append(
                        f"{key_path}: expected boolean, got {type(value).__name__}"
                    )

    return errors


def to_episode_card(
    ep: Dict, scored: Any = None, queue_position: int = None
) -> EpisodeCard:
    """Convert raw episode dict (or Pydantic Episode from algorithm) to EpisodeCard."""
    if hasattr(ep, "model_dump"):
        ep = ep.model_dump()
    series_data = ep.get("series") or {}
    scores_data = ep.get("scores") or {}
    return EpisodeCard(
        id=ep["id"],
        content_id=ep.get("content_id", ep["id"]),
        title=ep.get("title", ""),
        series=SeriesInfo(
            id=series_data.get("id", ""),
            name=series_data.get("name", ""),
        ),
        published_at=ep.get("published_at", ""),
        scores=EpisodeScores(**scores_data),
        badges=[],
        key_insight=ep.get("key_insight"),
        categories=ep.get("categories", {"major": [], "subcategories": []}),
        similarity_score=round(scored.similarity_score, 4) if scored else None,
        quality_score=round(scored.quality_score, 4) if scored else None,
        recency_score=round(scored.recency_score, 4) if scored else None,
        final_score=round(scored.final_score, 4) if scored else None,
        queue_position=queue_position,
    )
