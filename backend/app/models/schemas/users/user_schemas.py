import uuid
from typing import List

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserPublic(SQLModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool


class UserCreate(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    is_active: bool = True
    is_superuser: bool = False


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None


class DeleteUser(SQLModel):
    id: uuid.UUID
    message: str


class UsersPublic(SQLModel):
    data: List[UserPublic]
    count: int
