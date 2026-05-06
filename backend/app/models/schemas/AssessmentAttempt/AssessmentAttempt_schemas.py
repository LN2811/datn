import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AssessmentAttemptBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )

    project_id: uuid.UUID = Field(
        foreign_key="projects.id",
        nullable=False,
        index=True
    )

    assignment_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="assignments.id",
        index=True,
    )

    started_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )

    submitted_at: Optional[datetime] = None

    time_limit_minutes: Optional[int] = None

    is_submitted: bool = Field(default=False)
    is_time_up: bool = Field(default=False)

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AssessmentAttemptCreate(AssessmentAttemptBase):
    pass

class AssessmentAttemptRead(AssessmentAttemptBase):
    pass

class AssessmentAttemptUpdate(SQLModel):
    submitted_at: Optional[datetime] = None
    is_submitted: Optional[bool] = None
    is_time_up: Optional[bool] = None

