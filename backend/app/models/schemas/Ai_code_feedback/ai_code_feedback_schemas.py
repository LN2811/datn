import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AICodeFeedbackBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    submission_id: uuid.UUID = Field(
        foreign_key="code_submissions.id",
        nullable=False,
        index=True
    )
    overview: str = Field(nullable=False)
    code_quality_score: Optional[float] = Field(default=None, ge=0.0)
    logic_score: Optional[float] = Field(default=None, ge=0.0)
    performance_score: Optional[float] = Field(default=None, ge=0.0)
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    generated_by: str = Field(default="ai")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AICodeFeedbackCreate(AICodeFeedbackBase):
    pass

class AICodeFeedbackUpdate(SQLModel):
    overview: Optional[str] = None
    code_quality_score: Optional[float] = Field(default=None, ge=0.0)
    logic_score: Optional[float] = Field(default=None, ge=0.0)
    performance_score: Optional[float] = Field(default=None, ge=0.0)
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAICodeFeedback(SQLModel):
    id: uuid.UUID
    message: str