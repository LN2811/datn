import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class LearningMaterialBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    title: str = Field(nullable=False, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=512)
    external_link: Optional[str] = Field(default=None, max_length=512)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class LearningMaterialCreate(LearningMaterialBase):
    pass

class LearningMaterialUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=512)
    external_link: Optional[str] = Field(default=None, max_length=512)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class DeleteLearningMaterial(SQLModel):
    id: uuid.UUID
    message: str