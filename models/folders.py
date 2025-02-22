from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[UUID] = None
    tags: Optional[str] = None

    class Config:
        orm_mode = True

class FolderCreate(FolderBase):
    pass

class FolderUpdate(FolderBase):
    id: UUID

class FolderResponse(FolderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
