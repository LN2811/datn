import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class QuestionOptionBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    question_id: uuid.UUID = Field(
        foreign_key="questions.id",
        nullable=False
    )

    content: str = Field(nullable=False)

    is_correct: bool = Field(default=False)

    order_index: Optional[int] = Field(default=None)

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class QuestionOptionCreate(SQLModel):
    question_id: uuid.UUID
    content: str
    is_correct: Optional[bool] = False
    order_index: Optional[int] = None

class QuestionOptionUpdate(SQLModel):
    content: Optional[str] = None
    is_correct: Optional[bool] = None
    order_index: Optional[int] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteQuestionOption(SQLModel):
    id: uuid.UUID
    message: str