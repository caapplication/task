from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class ClosureRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class TaskClosureRequestBase(BaseModel):
    task_id: UUID
    reason: Optional[str] = None

class TaskClosureRequestCreate(TaskClosureRequestBase):
    pass

class TaskClosureRequestUpdate(BaseModel):
    status: ClosureRequestStatus
    reason: Optional[str] = None

class TaskClosureRequest(TaskClosureRequestBase):
    id: UUID
    requested_by: UUID
    status: ClosureRequestStatus
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

