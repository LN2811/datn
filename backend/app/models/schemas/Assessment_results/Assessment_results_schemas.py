import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AssessmentResultBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id",
        nullable=False,
        index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False
    )
    total_score: Optional[float] = Field(default=None, ge=0.0)
    passed: Optional[bool] = Field(default=None)
    completed_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )
    updated_at: Optional[datetime] = Field( 
        default_factory=datetime.utcnow,
        nullable=True
    )

class AssessmentResultCreate(SQLModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    total_score: Optional[float] = None
    passed: Optional[bool] = None
    completed_at: Optional[datetime] = None
    
class AssessmentResultUpdate(SQLModel):
    total_score: Optional[float] = Field(default=None, ge=0.0)
    passed: Optional[bool] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAssessmentResult(SQLModel):
    id: uuid.UUID
    message: str