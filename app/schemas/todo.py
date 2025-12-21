from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime

class TodoBase(BaseModel):
    title: str
    details: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    repeat_interval: Optional[str] = None  # 'day', 'week', 'month', 'year'
    repeat_every: Optional[int] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    details: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    repeat_interval: Optional[str] = None
    repeat_every: Optional[int] = None
    is_completed: Optional[bool] = None

class Todo(TodoBase):
    id: UUID
    agency_id: UUID
    is_completed: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

