"""Pure helpers: config merge, schema validation, episode card formatting."""

from typing import Any, Dict, List

# Session/recommendation constants (used by routes/sessions)
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20

try:
    from .models import EpisodeCard, EpisodeScores, SeriesInfo
except ImportError:
    from models import EpisodeCard, EpisodeScores, SeriesInfo


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


def get_badges(ep: Dict) -> List[str]:
    """Determine badges for an episode based on its scores."""
    badges = []
    scores = ep.get("scores", {})

    if (scores.get("insight") or 0) >= 3:
        badges.append("high_insight")
    if (scores.get("credibility") or 0) >= 3:
        badges.append("high_credibility")
    if (scores.get("information") or 0) >= 3:
        badges.append("data_rich")
    if (scores.get("entertainment") or 0) >= 3:
        badges.append("engaging")

    return badges[:2]


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
        badges=get_badges(ep),
        key_insight=ep.get("key_insight"),
        categories=ep.get("categories", {"major": [], "subcategories": []}),
        similarity_score=round(scored.similarity_score, 4) if scored else None,
        quality_score=round(scored.quality_score, 4) if scored else None,
        recency_score=round(scored.recency_score, 4) if scored else None,
        final_score=round(scored.final_score, 4) if scored else None,
        queue_position=queue_position,
    )
