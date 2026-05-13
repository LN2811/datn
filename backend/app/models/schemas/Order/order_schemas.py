import uuid 
from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

class OrderBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    plan_id: uuid.UUID = Field(foreign_key="pricing_plans.id", nullable=False, index=True)
    order_code: str = Field(max_length=100, unique=True, index=True)
    plan_name: str = Field(max_length=255)
    amount: int
    currency: str = Field(default="VND", max_length=10)
    payment_method: str = Field(default="momo", max_length=50)
    status: str = Field(default="pending", max_length=30)
    payment_status: str = Field(default="unpaid", max_length=30)
    paid_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: uuid.UUID   

class OrderUpdate(SQLModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    paid_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

