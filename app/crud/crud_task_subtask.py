from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.models.task_subtask import TaskSubtask
from app.models.task import Task
from app.models.activity_log import ActivityLog
from app.schemas.task_subtask import TaskSubtaskCreate, TaskSubtaskUpdate

def create_subtask(
    db: Session,
    task_id: UUID,
    subtask: TaskSubtaskCreate,
    agency_id: UUID,
    user_id: UUID
) -> Optional[TaskSubtask]:
    # Verify task exists and belongs to agency
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.agency_id == agency_id)
    ).first()
    if not task:
        return None
    
    # Get max sort_order for this task
    max_order = db.query(TaskSubtask).filter(TaskSubtask.task_id == task_id).count()
    
    # Exclude sort_order from subtask_data since we're setting it explicitly
    subtask_data = subtask.model_dump(exclude={'sort_order'})
    db_subtask = TaskSubtask(
        **subtask_data,
        task_id=task_id,
        sort_order=max_order
    )
    db.add(db_subtask)
    db.commit()
    db.refresh(db_subtask)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action=f"Subtask added: {db_subtask.title}",
        details=f"Subtask '{db_subtask.title}' was added to task",
        event_type="subtask_created"
    )
    db.add(activity_log)
    db.commit()
    
    return db_subtask

def get_subtask(db: Session, subtask_id: UUID, task_id: UUID, agency_id: UUID) -> Optional[TaskSubtask]:
    return db.query(TaskSubtask).join(Task).filter(
        and_(
            TaskSubtask.id == subtask_id,
            TaskSubtask.task_id == task_id,
            Task.agency_id == agency_id
        )
    ).first()

def get_subtasks_by_task(db: Session, task_id: UUID, agency_id: UUID) -> List[TaskSubtask]:
    return db.query(TaskSubtask).join(Task).filter(
        and_(
            TaskSubtask.task_id == task_id,
            Task.agency_id == agency_id
        )
    ).order_by(TaskSubtask.sort_order).all()

def update_subtask(
    db: Session,
    subtask_id: UUID,
    task_id: UUID,
    subtask_update: TaskSubtaskUpdate,
    agency_id: UUID,
    user_id: UUID
) -> Optional[TaskSubtask]:
    db_subtask = get_subtask(db, subtask_id, task_id, agency_id)
    if not db_subtask:
        return None
    
    update_data = subtask_update.model_dump(exclude_unset=True)
    old_completed = db_subtask.is_completed
    
    for key, value in update_data.items():
        if value is not None:
            setattr(db_subtask, key, value)
    
    db_subtask.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_subtask)
    
    # Create activity log if completion status changed
    if old_completed != db_subtask.is_completed:
        activity_log = ActivityLog(
            task_id=task_id,
            user_id=user_id,
            action=f"Subtask {'completed' if db_subtask.is_completed else 'uncompleted'}: {db_subtask.title}",
            details=f"Subtask '{db_subtask.title}' was marked as {'completed' if db_subtask.is_completed else 'uncompleted'}",
            event_type="subtask_updated",
            from_value={"is_completed": old_completed},
            to_value={"is_completed": db_subtask.is_completed}
        )
        db.add(activity_log)
        db.commit()
    
    return db_subtask

def delete_subtask(
    db: Session,
    subtask_id: UUID,
    task_id: UUID,
    agency_id: UUID,
    user_id: UUID
) -> bool:
    db_subtask = get_subtask(db, subtask_id, task_id, agency_id)
    if not db_subtask:
        return False
    
    subtask_title = db_subtask.title
    
    # Create activity log before deletion
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action=f"Subtask deleted: {subtask_title}",
        details=f"Subtask '{subtask_title}' was deleted",
        event_type="subtask_deleted"
    )
    db.add(activity_log)
    
    db.delete(db_subtask)
    db.commit()
    return True

