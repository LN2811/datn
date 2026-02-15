import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AIUsageLogBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    project_id: Optional[uuid.UUID] = Field(
        foreign_key="projects.id",
        default=None
    )
    action_type: str = Field(nullable=False)
    tokens_used: Optional[int] = None
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AIUsageLogCreate(AIUsageLogBase):
    pass

class AIUsageLogUpdate(SQLModel):
    action_type: Optional[str] = None
    tokens_used: Optional[int] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAIUsageLog(SQLModel):
    id: uuid.UUID
    message: str
