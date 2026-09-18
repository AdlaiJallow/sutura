from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.common.config import get_settings
from app.common.database import get_db
from app.common.errors import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

# D-026: the refresh token lives only in an httpOnly cookie, scoped to the auth path so it is
# never sent on unrelated API requests. `secure` follows the environment so local HTTP dev still
# works (browsers silently drop `Secure` cookies over plain HTTP).
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="lax",
        secure=settings.environment == "production",
        httponly=True,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    user = AuthService(db).register(payload)
    return RegisterResponse(id=user.id, email=user.email, is_email_verified=user.is_email_verified)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    access, raw_refresh = AuthService(db).login(payload.email, payload.password)
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> AccessTokenResponse:
    if not refresh_token:
        raise UnauthorizedError("Missing refresh token.")
    access, new_raw_refresh = AuthService(db).refresh(refresh_token)
    _set_refresh_cookie(response, new_raw_refresh)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> None:
    if refresh_token:
        AuthService(db).logout(refresh_token)
    _clear_refresh_cookie(response)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> None:
    AuthService(db).verify_email(payload.token)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)) -> None:
    AuthService(db).resend_verification(payload.email)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    AuthService(db).forgot_password(payload.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    AuthService(db).reset_password(payload.token, payload.new_password)
