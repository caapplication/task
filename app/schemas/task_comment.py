from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskCommentBase(BaseModel):
    message: str

class TaskCommentCreate(TaskCommentBase):
    pass

class TaskCommentUpdate(BaseModel):
    message: Optional[str] = None

class TaskComment(TaskCommentBase):
    id: UUID
    task_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

