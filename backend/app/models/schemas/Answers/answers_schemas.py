import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AnswerBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(
        foreign_key="questions.id",
        nullable=False
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False
    )
    score: Optional[int] = Field(default=None, ge=1, le=5)
    selected_option_id: Optional[uuid.UUID] = Field(
        foreign_key="question_options.id",
        default=None
    )
    text_answer: Optional[str] = Field(default=None)
    is_correct: Optional[bool] = Field(default=None)
    answered_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AnswerCreate(SQLModel):
    question_id: uuid.UUID
    user_id: uuid.UUID

    score: Optional[int] = None
    selected_option_id: Optional[uuid.UUID] = None
    text_answer: Optional[str] = None

class AnswerUpdate(SQLModel):
    score: Optional[int] = Field(default=None, ge=1, le=5)
    selected_option_id: Optional[uuid.UUID] = None
    text_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAnswer(SQLModel):
    id: uuid.UUID
    message: str