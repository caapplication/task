from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from enum import Enum

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    hold = "hold"

class TaskPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class DocumentRequestItem(BaseModel):
    name: str
    required: bool = False

class DocumentRequest(BaseModel):
    enabled: bool = False
    items: List[DocumentRequestItem] = []

class TaskBase(BaseModel):
    title: str
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    target_date: Optional[date] = None
    priority: Optional[TaskPriority] = None
    tag_id: Optional[UUID] = None
    document_request: Optional[DocumentRequest] = None
    assigned_to: Optional[UUID] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    target_date: Optional[date] = None
    priority: Optional[TaskPriority] = None
    tag_id: Optional[UUID] = None
    document_request: Optional[DocumentRequest] = None
    assigned_to: Optional[UUID] = None

class Task(TaskBase):
    id: UUID
    agency_id: UUID
    status: TaskStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    total_logged_seconds: Optional[int] = 0
    is_timer_running_for_me: Optional[bool] = False
    subtasks: Optional[List[dict]] = []  # Serialized as dict from router

    class Config:
        from_attributes = True
        populate_by_name = True

class TaskListItem(BaseModel):
    """Lightweight schema for list views"""
    id: UUID
    title: str
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    status: TaskStatus
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    assigned_to: Optional[UUID] = None
    tag_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

