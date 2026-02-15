import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class CurriculumBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id",
        nullable=False,
        index=True
    )
    title: str = Field(nullable=False)
    overview: Optional[str] = None
    generated_by: str = Field(default="ai")
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class CurriculumCreate(CurriculumBase):
    pass    

class CurriculumUpdate(SQLModel):
    title: Optional[str] = None
    overview: Optional[str] = None
    generated_by: Optional[str] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteCurriculum(SQLModel):
    id: uuid.UUID
    message: str