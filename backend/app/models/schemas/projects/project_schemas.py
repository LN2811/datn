import uuid 
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class ProjectBase(SQLModel):
    name: str = Field(nullable=False, index=True, max_length=255)
    is_active : bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class ProjectCreate(ProjectBase):
    account_id: str = Field(default=None, nullable=True, max_length=255)
    pass

class ProjectUpdate(SQLModel):
    name: Optional[str] = Field(default=None, index=True, max_length=255)
    is_active : Optional[bool] = Field(default=None)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class DeleteProject(SQLModel):
    id: uuid.UUID
    message: str

class ProjectsPublic(ProjectBase):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str