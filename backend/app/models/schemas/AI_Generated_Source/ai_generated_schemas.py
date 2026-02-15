import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AIGeneratedSourceBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id",
        nullable=False,
        index=True
    )
    source_url: Optional[str] = None
    title: Optional[str] = None
    content_summary: Optional[str] = None
    source_type: str = Field(default="web")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AIGeneratedSourceCreate(AIGeneratedSourceBase):
    pass

class AIGeneratedSourceUpdate(SQLModel):
    source_url: Optional[str] = None
    title: Optional[str] = None
    content_summary: Optional[str] = None
    source_type: Optional[str] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAIGeneratedSource(SQLModel):
    id: uuid.UUID
    message: str
