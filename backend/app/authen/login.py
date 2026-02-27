from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlmodel import select
from app.models.models import Users
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    def __init__(self, session):
        self.session = session

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_minutes: int = 15):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

    def login(self, email: str, password: str):

        user = self.session.exec(
            select(Users).where(Users.email == email)
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not self.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is inactive")

        access_token = self.create_access_token(
            data={
                "sub": str(user.id),
                "is_superuser": user.is_superuser
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }