from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import smtplib
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import select

from app.core.config import settings
from app.models.models import Users

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    def __init__(self, session):
        self.session = session

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_minutes: Optional[int] = None):
        effective_expiry = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=effective_expiry)
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

    def check_email_exists(self, email: str):
        user = self.session.exec(
            select(Users).where(Users.email == email)
        ).first()
        return user is not None

    @staticmethod
    def create_reset_token(email: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS
        )
        return jwt.encode(
            {
                "sub": email,
                "type": "password_reset",
                "exp": expire,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_token(token: str) -> str:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            ) from exc

        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "password_reset" or not isinstance(email, str) or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )

        return email

    def reset_password(self, email: str, new_password: str):
        user = self.session.exec(
            select(Users).where(Users.email == email)
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.hashed_password = pwd_context.hash(new_password)
        self.session.add(user)
        self.session.commit()
        return {"message": "Password updated"}

    @staticmethod
    def send_reset_email(to_email: str, token: str) -> str:
        reset_link = f"{settings.FRONTEND_HOST.rstrip('/')}/reset-password?token={token}"

        if not settings.SMTP_HOST:
            print(f"Password reset link for {to_email}: {reset_link}")
            return reset_link

        subject = "Reset mat khau"
        body = f"""
        click vao link o ben duoi de dat lai mat khau:
        {reset_link}
        Link co hieu luc trong {settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS} gio
        """
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER or "noreply@example.com"
        msg["To"] = to_email

        smtp_client = smtplib.SMTP_SSL if settings.SMTP_SSL else smtplib.SMTP
        with smtp_client(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS and not settings.SMTP_SSL:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return reset_link
