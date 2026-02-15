import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class UserSubscriptionBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    plan_id: uuid.UUID = Field(
        foreign_key="pricing_plans.id",
        nullable=False,
        index=True
    )
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class UserSubscriptionCreate(UserSubscriptionBase):
    pass   

class UserSubscriptionUpdate(SQLModel):
    plan_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="pricing_plans.id",
        index=True
    )
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class DeleteUserSubscription(SQLModel):
    id: uuid.UUID
    message: str
