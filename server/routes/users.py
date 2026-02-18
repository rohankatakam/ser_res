"""User enter: resolve or create by display name (no password). User engagements (Firestore)."""

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

try:
    from ..state import get_state
    from ..models import UserEnterRequest, UserResponse, EngageRequest
except ImportError:
    from state import get_state
    from models import UserEnterRequest, UserResponse, EngageRequest

router = APIRouter()

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
            detail="User store not configured. Set DATA_SOURCE=firebase and FIREBASE_CREDENTIALS_PATH in .env to your service account JSON path.",
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
        user = store.create(name)
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
