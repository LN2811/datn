import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class PricingPlanBase(SQLModel):
    name: str = Field(nullable=False)
    description: Optional[str] = None
    price: float = Field(default=0.0, ge=0.0)
    ai_usage_limit: Optional[int] = None
    billing_cycle: str = Field(default="monthly")
    max_project: Optional[int] = None
    max_projects: Optional[int] = None
    is_active: bool = Field(default=True)
    is_featured: bool = Field(default=False)
    display_order: int = Field(default=0)
    bagde_text: Optional[str] = None
    badge_text: Optional[str] = None

class PricingPlanCreate(PricingPlanBase):
    pass

class PricingPlanUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    ai_usage_limit: Optional[int] = None
    billing_cycle: Optional[str] = None
    max_project: Optional[int] = None
    max_projects: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    bagde_text: Optional[str] = None
    badge_text: Optional[str] = None

class PricingPlanPublic(PricingPlanBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    update_at: Optional[datetime] = None

class DeletePricingPlan(SQLModel):
    id: uuid.UUID
    message: str
