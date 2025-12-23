from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskStageBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_completed: bool = False
    is_blocked: bool = False

class TaskStageCreate(TaskStageBase):
    pass

class TaskStageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_completed: Optional[bool] = None
    is_blocked: Optional[bool] = None

class TaskStage(TaskStageBase):
    id: UUID
    agency_id: UUID
    is_default: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

