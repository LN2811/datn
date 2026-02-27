from fastapi import Request, HTTPException, status
from sqlmodel import Session
from app.models.models import Users
from app.core.database import engine
from app.core.security import decode_token


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

        with Session(engine) as session:
            user = session.get(Users, user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            return user
    
    def required_admin(
        self,
        request: Request,
    ) -> Users:

        user = self.get_current_user(request)

        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )

        return user