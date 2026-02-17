"""Request/response models for user enter (resolve or create by name)."""

from typing import Optional

from pydantic import BaseModel, model_validator


class UserEnterRequest(BaseModel):
    """Enter by display name (resolve or create) or by user_id (lookup)."""

    display_name: Optional[str] = None
    user_id: Optional[str] = None

    @model_validator(mode="after")
    def require_one(self):
        if not (self.display_name or self.user_id):
            raise ValueError("Provide display_name or user_id")
        return self


class UserResponse(BaseModel):
    """User returned after enter or get."""

    user_id: str
    display_name: str
    created: Optional[bool] = None  # True if new user was created (only when entering by display_name)
