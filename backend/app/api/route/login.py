from fastapi import APIRouter, Response

from app.api.deps import SessionDep
from app.authen.login import AuthService
from app.core.config import settings

router = APIRouter()

@router.post("/login")
def login(
    email: str,
    password: str,
    response: Response,
    session: SessionDep,
):
    service = AuthService(session)
    result = service.login(email, password)
    response.set_cookie(
        key="token",
        value=result["access_token"],
        httponly=True,
        secure=settings.ENVIRONMENT not in {"local", "development"},
        samesite="lax",
    )
    return {"message": "login successful"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="token",
        path="/",
        secure=settings.ENVIRONMENT not in {"local", "development"},
        samesite="lax",
    )
    return {"message": "logout successful"}
