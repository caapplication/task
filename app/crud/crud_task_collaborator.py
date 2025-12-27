from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional

from app.models.task_collaborator import TaskCollaborator
from app.models.activity_log import ActivityLog

def add_collaborator(
    db: Session,
    task_id: UUID,
    user_id: UUID,
    added_by: UUID
) -> TaskCollaborator:
    """Add a collaborator to a task"""
    # Check if collaborator already exists
    existing = db.query(TaskCollaborator).filter(
        and_(
            TaskCollaborator.task_id == task_id,
            TaskCollaborator.user_id == user_id
        )
    ).first()
    
    if existing:
        return existing  # Already a collaborator
    
    db_collaborator = TaskCollaborator(
        task_id=task_id,
        user_id=user_id,
        added_by=added_by
    )
    db.add(db_collaborator)
    db.commit()
    db.refresh(db_collaborator)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=added_by,
        action="Collaborator added",
        details=f"Added a collaborator to the task",
        event_type="collaborator_added",
        to_value={"collaborator_id": str(user_id)}
    )
    db.add(activity_log)
    db.commit()
    
    return db_collaborator

def remove_collaborator(
    db: Session,
    task_id: UUID,
    user_id: UUID,
    removed_by: UUID
) -> bool:
    """Remove a collaborator from a task"""
    db_collaborator = db.query(TaskCollaborator).filter(
        and_(
            TaskCollaborator.task_id == task_id,
            TaskCollaborator.user_id == user_id
        )
    ).first()
    
    if not db_collaborator:
        return False
    
    # Create activity log before deletion
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=removed_by,
        action="Collaborator removed",
        details=f"Removed a collaborator from the task",
        event_type="collaborator_removed",
        from_value={"collaborator_id": str(user_id)}
    )
    db.add(activity_log)
    
    db.delete(db_collaborator)
    db.commit()
    return True

def get_task_collaborators(
    db: Session,
    task_id: UUID
) -> List[TaskCollaborator]:
    """Get all collaborators for a task"""
    return db.query(TaskCollaborator).filter(
        TaskCollaborator.task_id == task_id
    ).all()

def is_collaborator(
    db: Session,
    task_id: UUID,
    user_id: UUID
) -> bool:
    """Check if a user is a collaborator on a task"""
    return db.query(TaskCollaborator).filter(
        and_(
            TaskCollaborator.task_id == task_id,
            TaskCollaborator.user_id == user_id
        )
    ).first() is not None

