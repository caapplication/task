from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskTimerBase(BaseModel):
    notes: Optional[str] = None

class TaskTimerCreate(TaskTimerBase):
    pass

class ManualTimeEntry(BaseModel):
    duration_seconds: int
    notes: Optional[str] = None
    date: Optional[datetime] = None

class TaskTimer(TaskTimerBase):
    id: UUID
    task_id: UUID
    user_id: UUID
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

