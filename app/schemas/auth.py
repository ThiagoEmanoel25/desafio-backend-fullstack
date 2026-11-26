"""Authentication schemas.

Login is form data (`OAuth2PasswordRequestForm`), so there is no `LoginRequest`.
`UserResponse` never exposes `hashed_password`.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload to create a new account."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Bearer token returned by a successful login."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public view of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    created_at: datetime
