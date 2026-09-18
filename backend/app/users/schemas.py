import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


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
    new_password: str
