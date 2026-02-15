import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class PricingPlanBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = None
    price: float = Field(default=0.0, ge=0.0)
    ai_usage_limit: Optional[int] = None
    max_projects: Optional[int] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class PricingPlanCreate(PricingPlanBase):
    pass

class PricingPlanUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    ai_usage_limit: Optional[int] = None
    max_projects: Optional[int] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class DeletePricingPlan(SQLModel):
    id: uuid.UUID
    message: str