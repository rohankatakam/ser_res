"""User enter: resolve or create by display name (no password). User engagements (Firestore)."""

import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

try:
    from ..state import get_state
    from ..models import UserEnterRequest, UserResponse, EngageRequest, UpdateCategoryInterestsRequest
    from ..services import EmbeddingGenerator
except ImportError:
    from state import get_state
    from models import UserEnterRequest, UserResponse, EngageRequest, UpdateCategoryInterestsRequest
    from services import EmbeddingGenerator

router = APIRouter()

# Embedding model for category interests (must match episode embeddings)
_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIMENSIONS = 1536

# Username: one string, no spaces, alphanumeric and underscore only
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def _validate_username(name: str) -> None:
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if not USERNAME_PATTERN.match(name.strip()):
        raise HTTPException(
            status_code=400,
            detail="Username must be one word: letters, numbers, and underscores only (no spaces or special characters).",
        )


def _normalize_username(name: str) -> str:
    return name.strip().lower()


@router.post("/enter", response_model=UserResponse)
def user_enter(request: UserEnterRequest):
    """
    Enter with display name or user_id.
    - If display_name is provided: return existing user with that name, or create a new user (Create User mode).
    - If user_id is provided: return that user or 404 (Login mode).
    Username must be one string with no spaces or special characters.
    """
    state = get_state()
    store = getattr(state, "user_store", None)
    if not store:
        raise HTTPException(
            status_code=503,
            detail="User store not configured. Set FIREBASE_CREDENTIALS_PATH in .env to your service account JSON path.",
        )
    if request.user_id:
        user_id = _normalize_username(request.user_id)
        _validate_username(request.user_id)
        user = store.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User does not exist")
        return UserResponse(
            user_id=user.get("user_id", user.get("id", "")),
            display_name=user.get("display_name", user.get("name", "")),
        )
    if request.display_name:
        _validate_username(request.display_name)
        name = request.display_name.strip()
        existing = store.get_by_display_name(name)
        if existing:
            return UserResponse(
                user_id=existing.get("user_id", existing.get("id", "")),
                display_name=existing.get("display_name", existing.get("name", "")),
                created=False,
            )
        category_interests: Optional[List[str]] = None
        category_vector: Optional[List[float]] = None
        if request.category_interests:
            ci = [c.strip() for c in request.category_interests if c and c.strip()]
            if ci:
                category_interests = ci
                api_key = getattr(get_state().config, "openai_api_key", None) or ""
                if api_key.strip():
                    algo = get_state().current_algorithm
                    model = algo.embedding_model if algo else _EMBEDDING_MODEL
                    dims = algo.embedding_dimensions if algo else _EMBEDDING_DIMENSIONS
                    try:
                        gen = EmbeddingGenerator(api_key=api_key.strip(), model=model, dimensions=dims)
                        text = ", ".join(category_interests)
                        vectors = gen.generate_batch([text])
                        if vectors:
                            category_vector = vectors[0]
                    except Exception as e:
                        print(f"[user] Category embedding failed: {e}, storing interests only")
        user = store.create(name, category_interests=category_interests, category_vector=category_vector)
        return UserResponse(
            user_id=user.get("user_id", user.get("id", "")),
            display_name=user.get("display_name", user.get("name", "")),
            created=True,
        )
    raise HTTPException(status_code=400, detail="Provide display_name or user_id")


# ---------------------------------------------------------------------------
# User engagements (Firestore users/{user_id}/engagements)
# ---------------------------------------------------------------------------


@router.post("/engagements")
def record_user_engagement(request: EngageRequest):
    """
    Record one engagement (click/bookmark) for a user. Does not require a session.
    Use this so engagements are persisted when user clicks from Browse or before a session exists.
    Requires user_id in the body when Firestore is configured.
    """
    state = get_state()
    user_id = request.user_id
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required to record an engagement")
    state.engagement_store.record_engagement(
        user_id.strip(),
        request.episode_id,
        request.type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        episode_title=request.episode_title,
        series_name=request.series_name,
    )
    return {"status": "ok", "episode_id": request.episode_id, "type": request.type}


@router.get("/engagements")
def get_user_engagements(user_id: Optional[str] = Query(None, description="User ID (required for Firestore)")):
    """Get engagements for a user. When Firestore is configured, returns stored engagements; otherwise empty."""
    state = get_state()
    if not user_id or not user_id.strip():
        return {"engagements": []}
    engagements = state.engagement_store.get_engagements_for_ranking(user_id.strip(), [])
    return {"engagements": engagements}


@router.post("/engagements/reset")
def reset_user_engagements(user_id: Optional[str] = Query(None, description="User ID to clear engagements for")):
    """Clear all engagements for the user (e.g. Reset feed). No-op when engagement store is request-only."""
    state = get_state()
    if user_id and user_id.strip():
        state.engagement_store.delete_all_engagements(user_id.strip())
    return {"status": "ok", "message": "Engagements reset"}


@router.delete("/engagements/{engagement_id}")
def delete_user_engagement(
    engagement_id: str,
    user_id: Optional[str] = Query(None, description="User ID (required for Firestore)"),
):
    """Delete one engagement by Firestore document id. Returns 404 if not found or store does not support delete."""
    state = get_state()
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")
    deleted = state.engagement_store.delete_engagement(user_id.strip(), engagement_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Engagement not found or cannot be deleted")
    return {"status": "ok", "message": "Engagement deleted"}


# ---------------------------------------------------------------------------
# User profile (get user, update category interests)
# Must be after literal paths like /engagements so {user_id} does not match them.
# ---------------------------------------------------------------------------


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    """Get user by id. Returns user_id, display_name, category_interests.
    If user doc is missing but the id is valid, creates a minimal user (heals stale/migrated sessions)."""
    state = get_state()
    store = getattr(state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store not configured")
    uid = _normalize_username(user_id)
    if not uid:
        raise HTTPException(status_code=400, detail="Invalid user id")
    user = store.get_by_id(uid)
    if not user:
        # Heal: user may have session/engagements but no doc (migration, edge case).
        # Create minimal user so Interests and other profile flows work.
        try:
            user = store.create(uid)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        user_id=user.get("user_id", user.get("id", "")),
        display_name=user.get("display_name", user.get("name", "")),
        category_interests=user.get("category_interests"),
    )


@router.patch("/{user_id}/category-interests", response_model=UserResponse)
def update_category_interests(user_id: str, request: UpdateCategoryInterestsRequest):
    """Update category interests for a user. Re-embeds and stores category_vector."""
    state = get_state()
    store = getattr(state, "user_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="User store not configured")
    uid = _normalize_username(user_id)
    user = store.get_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ci = [c.strip() for c in request.category_interests if c and c.strip()]
    category_vector: Optional[List[float]] = None
    api_key = getattr(state.config, "openai_api_key", None) or ""
    if api_key.strip():
        algo = state.current_algorithm
        model = algo.embedding_model if algo else _EMBEDDING_MODEL
        dims = algo.embedding_dimensions if algo else _EMBEDDING_DIMENSIONS
        try:
            gen = EmbeddingGenerator(api_key=api_key.strip(), model=model, dimensions=dims)
            text = ", ".join(ci) if ci else ""
            if text:
                vectors = gen.generate_batch([text])
                if vectors:
                    category_vector = vectors[0]
        except Exception as e:
            print(f"[user] Category embedding failed: {e}")
    updated = store.update_category_interests(uid, ci, category_vector)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        user_id=updated.get("user_id", updated.get("id", "")),
        display_name=updated.get("display_name", updated.get("name", "")),
        category_interests=updated.get("category_interests"),
    )
