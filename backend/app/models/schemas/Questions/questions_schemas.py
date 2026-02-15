import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class QuestionBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    project_id: uuid.UUID = Field(foreign_key="projects.id", nullable=False)
    criteria_id: uuid.UUID = Field(foreign_key="criteria.id", nullable=False)
    content: str = Field(nullable=False)
    question_category: str = Field(default="assessment", max_length=30)
    question_type: str = Field(nullable=False, max_length=30)
    difficulty_level: str = Field(default="medium", max_length=20)
    generated_by: str = Field(default="ai", max_length=20)
    order_index: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class QuestionCreate(SQLModel):
    project_id: uuid.UUID
    criteria_id: uuid.UUID
    content: str
    question_type: str
    question_category: Optional[str] = "assessment"
    difficulty_level: Optional[str] = "medium"
    generated_by: Optional[str] = "ai"
    order_index: Optional[int] = None

class QuestionUpdate(SQLModel):
    content: Optional[str] = None
    question_type: Optional[str] = None
    question_category: Optional[str] = None
    difficulty_level: Optional[str] = None
    generated_by: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteQuestion(SQLModel):
    id: uuid.UUID
    message: str