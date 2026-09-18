from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.users.models import User
from app.users.schemas import ChangePasswordRequest, UserRead, UserUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


class DeactivateRequest(BaseModel):
    password: str


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return UserService(db).update_profile(current_user, payload)


@router.post("/me/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    UserService(db).change_password(current_user, payload)


@router.delete("/me", status_code=204)
def delete_me(
    payload: DeactivateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    UserService(db).deactivate(current_user, payload.password)
