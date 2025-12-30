from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models.task_timer import TaskTimer
from app.models.task import Task
from app.models.activity_log import ActivityLog
from app.schemas.task_timer import TaskTimerCreate, ManualTimeEntry

def start_timer(
    db: Session,
    task_id: UUID,
    agency_id: UUID,
    user_id: UUID
) -> Optional[TaskTimer]:
    # Verify task exists and belongs to agency
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.agency_id == agency_id)
    ).first()
    if not task:
        return None
    
    # Check if user has an active timer for this task
    active_timer = db.query(TaskTimer).filter(
        and_(
            TaskTimer.task_id == task_id,
            TaskTimer.user_id == user_id,
            TaskTimer.is_active == True
        )
    ).first()
    
    if active_timer:
        return active_timer  # Return existing active timer
    
    # Create new timer (use timezone-aware datetime)
    db_timer = TaskTimer(
        task_id=task_id,
        user_id=user_id,
        start_time=datetime.now(timezone.utc),
        is_active=True,
        duration_seconds=0
    )
    db.add(db_timer)
    db.commit()
    db.refresh(db_timer)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Timer started",
        details="Task timer was started",
        event_type="timer_started"
    )
    db.add(activity_log)
    db.commit()
    
    return db_timer

def stop_timer(
    db: Session,
    task_id: UUID,
    agency_id: UUID,
    user_id: UUID
) -> Optional[TaskTimer]:
    # Verify task exists and belongs to agency
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.agency_id == agency_id)
    ).first()
    if not task:
        return None
    
    # Find active timer for this user and task
    db_timer = db.query(TaskTimer).filter(
        and_(
            TaskTimer.task_id == task_id,
            TaskTimer.user_id == user_id,
            TaskTimer.is_active == True
        )
    ).first()
    
    if not db_timer:
        return None
    
    # Calculate duration (use timezone-aware datetime)
    end_time = datetime.now(timezone.utc)
    duration = int((end_time - db_timer.start_time).total_seconds())
    
    db_timer.end_time = end_time
    db_timer.duration_seconds = duration
    db_timer.is_active = False
    db.commit()
    db.refresh(db_timer)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Timer stopped",
        details=f"Task timer was stopped. Duration: {duration} seconds",
        event_type="timer_stopped",
        to_value={"duration_seconds": duration}
    )
    db.add(activity_log)
    db.commit()
    
    return db_timer

def add_manual_time(
    db: Session,
    task_id: UUID,
    time_entry: ManualTimeEntry,
    agency_id: UUID,
    user_id: UUID
) -> Optional[TaskTimer]:
    # Verify task exists and belongs to agency
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.agency_id == agency_id)
    ).first()
    if not task:
        return None
    
    entry_time = time_entry.date or datetime.now(timezone.utc)
    
    db_timer = TaskTimer(
        task_id=task_id,
        user_id=user_id,
        start_time=entry_time,
        end_time=entry_time + timedelta(seconds=time_entry.duration_seconds),
        duration_seconds=time_entry.duration_seconds,
        is_active=False,
        notes=time_entry.notes
    )
    db.add(db_timer)
    db.commit()
    db.refresh(db_timer)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Manual time entry added",
        details=f"Manual time entry: {time_entry.duration_seconds} seconds. {time_entry.notes or ''}",
        event_type="timer_manual",
        to_value={"duration_seconds": time_entry.duration_seconds}
    )
    db.add(activity_log)
    db.commit()
    
    return db_timer

def get_timers_by_task(db: Session, task_id: UUID, agency_id: UUID) -> List[TaskTimer]:
    return db.query(TaskTimer).join(Task).filter(
        and_(
            TaskTimer.task_id == task_id,
            Task.agency_id == agency_id
        )
    ).order_by(desc(TaskTimer.created_at)).all()

def get_active_timer(db: Session, task_id: UUID, user_id: UUID) -> Optional[TaskTimer]:
    return db.query(TaskTimer).filter(
        and_(
            TaskTimer.task_id == task_id,
            TaskTimer.user_id == user_id,
            TaskTimer.is_active == True
        )
    ).first()

