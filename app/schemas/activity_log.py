from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class ActivityLogBase(BaseModel):
    action: str
    details: Optional[str] = None
    event_type: Optional[str] = None
    from_value: Optional[Dict[str, Any]] = None
    to_value: Optional[Dict[str, Any]] = None

class ActivityLog(ActivityLogBase):
    id: UUID
    task_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

