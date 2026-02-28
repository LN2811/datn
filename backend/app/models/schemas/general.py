from enum import Enum
from uuid import UUID

from sqlmodel import Field, SQLModel

class Message(SQLModel):
    message: str

class Token (SQLModel):
    access_token: str
    token_type: str= "bearer"

class TokenPayload(SQLModel):
    sub: str | None = None

class NewPassWord(SQLModel):
    token: str
    new_password: str = Field(min_lenght = 8, max_lenght =40)

class QueryParams(SQLModel):
    page_size: int = Field(default=10, ge=1, le=100, alias="page_size")
    page_index: int = Field(default=1, ge=1, alias="page_index")
    sort_by: str | None = Field(default=None, alias="sort_by")
    sort_order: str | None = Field(default="asc", alias="sort_order")
    search: str | None = Field(default=None, alias="search")
