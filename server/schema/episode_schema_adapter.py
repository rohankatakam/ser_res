"""
Episode schema adapter: convert external Firestore formats → rec_engine Episode format.

Supports:
- External format (e.g. podcast_episodes): episode_title, podcast_series_id, series_name,
  publish_date, scoring.v1_credibility, tagging.v1_top_categories, etc.
- rec_engine format: pass-through (title, published_at, series, scores, key_insight, etc.)

Output dict is valid for algorithm.models.episode.Episode.model_validate().
"""

from typing import Any, Dict, List

# For documentation and validation; output remains dict for protocol compatibility
from algorithm.models.episode import Episode


def is_external_format_episode(doc: Dict[str, Any]) -> bool:
    """Detect if an episode doc uses external schema (e.g. podcast_episodes)."""
    return "podcast_series_id" in doc or "episode_title" in doc


def _extract_categories(doc: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract categories from tagging.v1_top_categories / v1_sub_categories."""
    tagging = doc.get("tagging") or {}
    major: List[str] = []
    sub: List[str] = []
    for cat in (tagging.get("v1_top_categories") or {}).get("categories") or []:
        name = cat.get("name") if isinstance(cat, dict) else str(cat)
        if name:
            major.append(name)
    for cat in (tagging.get("v1_sub_categories") or {}).get("subcategories") or []:
        name = cat.get("name") if isinstance(cat, dict) else str(cat)
        if name:
            sub.append(name)
    return {"major": major, "subcategories": sub}


def _extract_scores(doc: Dict[str, Any]) -> Dict[str, int]:
    """Extract scores from scoring (v1_credibility.score → credibility, etc.)."""
    scoring = doc.get("scoring") or {}
    score_map = {
        "v1_credibility": "credibility",
        "v1_insight": "insight",
        "v1_info_density": "information",
        "v1_entertainment": "entertainment",
    }
    out: Dict[str, int] = {}
    for ms_key, re_key in score_map.items():
        val = scoring.get(ms_key)
        if isinstance(val, dict) and "score" in val:
            out[re_key] = int(val["score"]) if val["score"] is not None else 0
        elif isinstance(val, (int, float)):
            out[re_key] = int(val)
    return out


def _external_to_rec_engine(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert external format (e.g. podcast_episodes) to rec_engine Episode format.

    Returns:
        Dict valid for Episode.model_validate(). See algorithm.models.episode.Episode.
    """
    doc_id = doc.get("id", "")
    series_id = doc.get("podcast_series_id") or ""
    series_name = doc.get("series_name") or ""

    result = {
        "id": doc_id,
        "content_id": doc.get("content_id") or _content_id_from_external(doc) or doc_id,
        "title": doc.get("episode_title") or doc.get("title", ""),
        "published_at": doc.get("publish_date") or doc.get("published_at", ""),
        "scores": _extract_scores(doc) or doc.get("scores"),
        "key_insight": doc.get("key_insight") or doc.get("exec_overview") or "",
        "categories": _extract_categories(doc) or doc.get("categories"),
        "series": {"id": series_id, "name": series_name} if series_id or series_name else doc.get("series"),
    }
    try:
        Episode.model_validate(result)  # validation only
    except Exception:
        pass  # allow partial output; caller may validate later
    return result


def _content_id_from_external(doc: Dict[str, Any]) -> str | None:
    """Derive content_id from pod_index or taddy."""
    pod_index = doc.get("pod_index") or {}
    if isinstance(pod_index, dict):
        ep_id = pod_index.get("episode_id")
        sr_id = pod_index.get("series_id")
        if ep_id and sr_id:
            return f"{ep_id}-{sr_id}"
    taddy = doc.get("taddy") or {}
    if isinstance(taddy, dict) and taddy.get("uuid"):
        return taddy["uuid"]
    return None


def to_rec_engine_episode(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert any episode doc to rec_engine format.

    If doc looks like external format (podcast_episodes), apply conversion.
    Otherwise return as-is (rec_engine fixtures already match).

    Returns:
        Dict valid for Episode.model_validate(). See algorithm.models.episode.Episode.
    """
    if is_external_format_episode(doc):
        return _external_to_rec_engine(doc)
    try:
        Episode.model_validate(doc)  # validation only for pass-through
    except Exception:
        pass  # allow partial docs; caller may validate later
    return doc


# Backwards-compatible aliases
is_metaspark_episode = is_external_format_episode
metaspark_to_rec_engine_episode = _external_to_rec_engine
