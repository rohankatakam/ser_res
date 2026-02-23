"""
Embedding Strategy for V1.2 Blended Scoring Algorithm

This module defines HOW text is extracted from episodes for embedding.
Changes to this module require regenerating embeddings (bump STRATEGY_VERSION).

The embedding text formula:
    "{title}. {key_insight}"  (full key_insight, no truncation)

This is used for BOTH:
- Episode embeddings (pre-computed, cached)
- User activity vectors (computed at request time using same formula)
"""

# Metadata for cache validation
# IMPORTANT: Bump this version when the embedding logic changes!
STRATEGY_VERSION = "1.1"

# OpenAI embedding configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def get_embed_text(episode: dict) -> str:
    """
    Generate text for embedding from an episode.

    Formula: "{title}. {key_insight}" (full key_insight, no truncation).

    This MUST be the same formula used for:
    - Pre-computing episode embeddings (e.g. for Pinecone)
    - Computing user activity vectors at request time

    Changes to this function require:
    1. Bumping STRATEGY_VERSION
    2. Regenerating embeddings for affected algorithm+dataset combos

    Args:
        episode: Episode dict with at least 'title' and optionally 'key_insight'

    Returns:
        Text string to be embedded
    """
    # Support both rec_engine (title) and metaspark (episode_title) field names
    title = episode.get("title") or episode.get("episode_title", "")
    key_insight = episode.get("key_insight") or ""

    embed_text = f"{title}. {key_insight}".strip()

    # Ensure we have something to embed
    if not embed_text or embed_text == ".":
        embed_text = title or "Untitled episode"

    return embed_text


def validate_episode_for_embedding(episode: dict) -> tuple[bool, str]:
    """
    Validate that an episode has the required fields for embedding.

    Returns:
        (is_valid, error_message)
    """
    if not episode.get("id"):
        return False, "Missing 'id' field"

    if not (episode.get("title") or episode.get("episode_title")):
        return False, "Missing 'title' or 'episode_title' field"

    return True, ""
