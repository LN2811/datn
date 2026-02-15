import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AssignmentBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id",
        nullable=False,
        index=True
    )
    title: str = Field(nullable=False)
    description: Optional[str] = None
    difficulty_level: str = Field(default="medium")
    assignment_type: str = Field(default="coding")
    generated_by: str = Field(default="ai")
    due_date: Optional[datetime] = None
    max_score: Optional[float] = Field(default=10.0)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    assignment_type: Optional[str] = None
    generated_by: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: Optional[float] = Field(default=None)
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class DeleteAssignment(SQLModel):
    id: uuid.UUID
    message: str