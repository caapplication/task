from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskCollaboratorBase(BaseModel):
    user_id: UUID

class TaskCollaboratorCreate(TaskCollaboratorBase):
    pass

class TaskCollaborator(TaskCollaboratorBase):
    id: UUID
    task_id: UUID
    added_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

