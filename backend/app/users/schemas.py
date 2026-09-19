import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    default_currency: str
    is_email_verified: bool
    mfa_enabled: bool
    is_active: bool


class UserUpdate(BaseModel):
    full_name: str | None = None
    default_currency: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    # Found in Phase 5 review: unlike RegisterRequest.password / ResetPasswordRequest.new_password,
    # this had no length constraint at all. Matches those two exactly now.
    new_password: str = Field(min_length=8, max_length=128)
