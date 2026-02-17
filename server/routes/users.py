"""User enter: resolve or create by display name (no password)."""

import re

from fastapi import APIRouter, HTTPException

try:
    from ..state import get_state
    from ..models import UserEnterRequest, UserResponse
except ImportError:
    from state import get_state
    from models import UserEnterRequest, UserResponse

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
            detail="User store not configured. Set DATA_SOURCE=json or DATA_SOURCE=firebase and FIREBASE_CREDENTIALS_PATH.",
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
