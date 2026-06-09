import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field

class AiusagequotaBase(SQLModel):
    id: uuid.UUID = Field(default_factory== uuid.UUID, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    token_used: Optional[int] = Field(default=None)
    reset_at: Optional[datetime] =Field(default_factory=datetime.utcnow, nullable=True)
    update_at: Optional[datetime] = Field(default_factory=datetime.utcnow, nullable=True)

class AiusagequotaCreate(SQLModel):
    user_id:uuid.UUID
    token_used: Optional[int] = None
    reset_at: Optional[datetime] = None
    update_at: Optional[datetime] = None

class AiusagequotaUpdate(SQLModel):
    token_used: Optional[int] = None
    reset_at: Optional[datetime] = None
    update_at: Optional[datetime] = None

