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
    order_index: Optional[int] = None
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class CurriculumModuleCreate(CurriculumModuleBase):
    pass    

class CurriculumModuleUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteCurriculumModule(SQLModel):
    id: uuid.UUID
    message: str
