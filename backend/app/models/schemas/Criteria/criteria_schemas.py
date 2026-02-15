import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class CriteriaBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)
    weight: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class CriteriaCreate(CriteriaBase):
    pass

class CriteriaUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)
    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_active: Optional[bool] = Field(default=None)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class DeleteCriteria(SQLModel):
    id: uuid.UUID
    message: str
