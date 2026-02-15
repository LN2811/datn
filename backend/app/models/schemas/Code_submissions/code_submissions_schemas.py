import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CodeSubmissionBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    assignment_id: uuid.UUID = Field(
        foreign_key="assignments.id",
        nullable=False,
        index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    github_repo_url: Optional[str] = None
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    score: Optional[float] = Field(default=None, ge=0.0)
    status: str = Field(default="submitted")
    submitted_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )
    graded_at: Optional[datetime] = None

class CodeSubmissionCreate(CodeSubmissionBase):
    pass

class CodeSubmissionUpdate(SQLModel):
    github_repo_url: Optional[str] = None
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    score: Optional[float] = Field(default=None, ge=0.0)
    status: Optional[str] = None
    graded_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteCodeSubmission(SQLModel):
    id: uuid.UUID
    message: str
