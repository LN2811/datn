import uuid

from fastapi import HTTPException, Request, status
from sqlmodel import Session

from app.models.models import Users
from app.core.db import engine
from app.core.sercurity import decode_token


class Authen:

    @staticmethod
    def get_current_user(request: Request) -> Users:

        token = request.cookies.get("token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        try:
            user_uuid = uuid.UUID(str(user_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from exc

        with Session(engine) as session:
            user = session.get(Users, user_uuid)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            return user

    @staticmethod
    def require_admin(request: Request) -> Users:
        user = Authen.get_current_user(request)

        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )

        return user
