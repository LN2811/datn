from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import sqlmodel

class MaterialChunkBase(BaseModel):
    material_id: UUID
    curriculum_module_id: Optional[UUID] = None
    content: str
    chunk_index: int

class MaterialChunkCreate(MaterialChunkBase):
    pass

class MaterialChunkUpdate(MaterialChunkBase):
    pass

class MaterialChunkRead(MaterialChunkBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
