from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskCommentReadBase(BaseModel):
    comment_id: UUID
    user_id: UUID

class TaskCommentReadCreate(TaskCommentReadBase):
    pass

class TaskCommentRead(TaskCommentReadBase):
    id: UUID
    read_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

