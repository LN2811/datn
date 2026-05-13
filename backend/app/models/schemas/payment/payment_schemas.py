import uuid
from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

class PaymentTransactionBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id")
    plan_id: uuid.UUID = Field(foreign_key="pricing_plans.id")
    amount: int
    currency: str
    payment_provider: str
    order_id: str = Field(max_length=100, unique=True)
    request_id: str = Field(max_length=100, unique=True)
    provider_transaction_id: Optional[str] = None
    pay_url: Optional[str] = Field(default=None, max_length=1024)
    deeplink: Optional[str] = Field(default=None, max_length=1024)
    qr_code_url: Optional[str] = Field(default=None, max_length=1024)
    status: str
    result_code: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=1024)
    paid_at: Optional[datetime] = None

class PaymentTransactionCreate(SQLModel):
    plan_id: uuid.UUID

class PaymentTransactionRead(PaymentTransactionBase):
    id: uuid.UUID
    update_at: datetime
    created_at: datetime
    paid_at: Optional[datetime] = None

class MomoCreateRequest(SQLModel):
    payment_id: uuid.UUID
    order_id: str
    amount: int
    pay_url: Optional[str] = Field(default=None, max_length=1024)
    deeplink: Optional[str] = Field(default=None, max_length=1024)
    qr_code_url: Optional[str] = Field(default=None, max_length=1024)
    message: Optional[str] = Field(default=None, max_length=1024)