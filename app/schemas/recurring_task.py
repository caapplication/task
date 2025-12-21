from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from enum import Enum

from app.schemas.task import DocumentRequest, TaskPriority

class RecurrenceFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"

class RecurringTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[UUID] = None
    tag_id: Optional[UUID] = None
    document_request: Optional[DocumentRequest] = None
    
    # Recurrence configuration
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, description="Every N days/weeks/months/years")
    start_date: date
    end_date: Optional[date] = None
    
    # Day of week/month configuration
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0-6 (Monday-Sunday) for weekly recurrence")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="1-31 for monthly recurrence")
    week_of_month: Optional[int] = Field(None, ge=1, le=4, description="1-4 (first-fourth week) for monthly recurrence")
    
    # Due date configuration
    due_date_offset: int = Field(default=0, description="Days to add to creation date for due_date")
    target_date_offset: Optional[int] = Field(None, description="Days to add to creation date for target_date")
    
    is_active: bool = True

class RecurringTaskCreate(RecurringTaskBase):
    pass

class RecurringTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[UUID] = None
    tag_id: Optional[UUID] = None
    document_request: Optional[DocumentRequest] = None
    
    frequency: Optional[RecurrenceFrequency] = None
    interval: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    week_of_month: Optional[int] = Field(None, ge=1, le=4)
    
    due_date_offset: Optional[int] = None
    target_date_offset: Optional[int] = None
    
    is_active: Optional[bool] = None

class RecurringTask(RecurringTaskBase):
    id: UUID
    agency_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

