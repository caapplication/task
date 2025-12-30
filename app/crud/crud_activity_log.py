from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from uuid import UUID
from typing import List, Optional

from app.models.activity_log import ActivityLog
from app.models.task import Task

def get_activity_logs_by_task(
    db: Session,
    task_id: UUID,
    agency_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[ActivityLog]:
    return db.query(ActivityLog).join(Task).filter(
        and_(
            ActivityLog.task_id == task_id,
            Task.agency_id == agency_id
        )
    ).order_by(desc(ActivityLog.created_at)).offset(skip).limit(limit).all()

def create_activity_log(
    db: Session,
    task_id: UUID,
    user_id: UUID,
    action: str,
    details: Optional[str] = None,
    event_type: Optional[str] = None,
    from_value: Optional[dict] = None,
    to_value: Optional[dict] = None
) -> ActivityLog:
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action=action,
        details=details,
        event_type=event_type,
        from_value=from_value,
        to_value=to_value
    )
    db.add(activity_log)
    db.commit()
    db.refresh(activity_log)
    return activity_log

