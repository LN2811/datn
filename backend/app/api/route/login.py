from fastapi import APIRouter, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import SessionDep
from app.authen.login import AuthService
from app.core.config import settings
from app.models.schemas.users.user_schemas import UserPublic, UserRegister
from app.services.users import UserService

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=255)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT not in {"local", "development"},
        samesite="lax",
    )


@router.post("/login")
def login(
    email: str,
    password: str,
    response: Response,
    session: SessionDep,
):
    service = AuthService(session)
    result = service.login(email, password)
    _set_auth_cookie(response, result["access_token"])
    return {"message": "login successful"}


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    response: Response,
    session: SessionDep,
) -> UserPublic:
    new_user = UserService.create_user(session=session, user_in=user_in)
    service = AuthService(session)
    result = service.login(user_in.email, user_in.password)
    _set_auth_cookie(response, result["access_token"])
    return new_user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="token",
        path="/",
        secure=settings.ENVIRONMENT not in {"local", "development"},
        samesite="lax",
    )
    return {"message": "logout successful"}


@router.post("/forgot-password")
@router.post("/forgot_password", include_in_schema=False)
def forgot_password(data: ForgotPasswordRequest, session: SessionDep):
    service = AuthService(session)
    response_data: dict[str, str] = {"message": "If email exists, reset link sent"}

    if not service.check_email_exists(data.email):
        return response_data

    token = service.create_reset_token(data.email)
    reset_link = service.send_reset_email(data.email, token)

    if settings.ENVIRONMENT in {"local", "development"}:
        response_data["reset_link"] = reset_link

    return response_data


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, session: SessionDep):
    service = AuthService(session)
    email = service.verify_reset_token(data.token)
    service.reset_password(email, data.password)
    return {"message": "Password reset successful"}
