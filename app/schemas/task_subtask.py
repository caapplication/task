from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskSubtaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_completed: bool = False
    sort_order: int = 0

class TaskSubtaskCreate(TaskSubtaskBase):
    pass

class TaskSubtaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    sort_order: Optional[int] = None

class TaskSubtask(TaskSubtaskBase):
    id: UUID
    task_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

