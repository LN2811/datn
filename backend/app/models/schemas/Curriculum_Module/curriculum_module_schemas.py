import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field


class CurriculumModuleBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    curriculum_id: uuid.UUID = Field(
        foreign_key="curriculums.id",
        nullable=False,
        index=True
    )
    title: str = Field(nullable=False)
    description: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    source_headings: Optional[List[str]] = None
    source_chunks: Optional[List[str]] = None
    heading_match_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    content: Optional[str] = None
    generate_status: str = "pending"
    is_preview: bool = False
    order_index: Optional[int] = None
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )


class CurriculumModulePublic(SQLModel):
    id: uuid.UUID
    curriculum_id: uuid.UUID
    title: str
    description: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    source_headings: Optional[List[str]] = None
    source_chunks: Optional[List[str]] = None
    heading_match_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    content: Optional[str] = None
    generate_status: str = "pending"
    is_preview: bool = False
    order_index: Optional[int] = None
    created_at: Optional[datetime] = None


class CurriculumModuleCreate(CurriculumModuleBase):
    pass


class CurriculumModuleUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    source_headings: Optional[List[str]] = None
    source_chunks: Optional[List[str]] = None
    content: Optional[str] = None
    generate_status: Optional[str] = None
    is_preview: Optional[bool] = None
    order_index: Optional[int] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )


class DeleteCurriculumModule(SQLModel):
    id: uuid.UUID
    message: str
