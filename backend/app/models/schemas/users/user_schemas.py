from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


class UserBase(SQLModel):
    email: EmailStr = Field(nullable=False, unique=True, index=True, max_length=255)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    account_name: str = Field(max_length=255,nullable=False)
    contact_email: Optional[EmailStr] = Field(default=None,max_length=255)
    contact_phone: Optional[str] = Field(default=None,max_length=50)
    pinned_at: Optional[datetime] = Field(default=None,nullable=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow,nullable=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow,nullable=True)

class UserCreate(UserBase):
    created_by_id: str = Field(default=None,nullable=True, max_length=255)
    pass

class UserUpdate(SQLModel):
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    hashed_password: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    is_admin: Optional[bool] = Field(default=None)
    account_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[EmailStr] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    pinned_at: Optional[datetime] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class DeleteUser(SQLModel):
    id: uuid.UUID
    message: str

class UserPublic(UserBase):
    id: uuid.UUID

class UsersPublic(SQLModel):
    data: List[UserPublic]
    count: int