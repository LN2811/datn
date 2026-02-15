import uuid 
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AIAnalysisBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    assessment_result_id: uuid.UUID = Field(
        foreign_key="assessment_results.id",
        nullable=False,
        index=True
    )
    analysis_text: str = Field(nullable=False)
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    recommendations: Optional[str] = None
    generated_by: str = Field(default="ai")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )

class AIAnalysisCreate(AIAnalysisBase):
    pass

class AIAnalysisUpdate(SQLModel):
    analysis_text: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    recommendations: Optional[str] = None
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        nullable=True
    )

class DeleteAIAnalysis(SQLModel):
    id: uuid.UUID
    message: str