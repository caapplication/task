from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.task_closure_request import TaskClosureRequest, ClosureRequestStatus
from app.schemas.task_closure_request import TaskClosureRequestCreate, TaskClosureRequestUpdate

def create_closure_request(
    db: Session,
    closure_request: TaskClosureRequestCreate,
    requested_by: UUID
) -> TaskClosureRequest:
    """Create a new task closure request"""
    # Check if there's already a pending request for this task
    existing = db.query(TaskClosureRequest).filter(
        and_(
            TaskClosureRequest.task_id == closure_request.task_id,
            TaskClosureRequest.status == ClosureRequestStatus.pending
        )
    ).first()
    
    if existing:
        return existing  # Return existing pending request
    
    db_request = TaskClosureRequest(
        task_id=closure_request.task_id,
        requested_by=requested_by,
        reason=closure_request.reason,
        status=ClosureRequestStatus.pending
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

def get_closure_request(
    db: Session,
    request_id: UUID,
    task_id: UUID
) -> Optional[TaskClosureRequest]:
    """Get a closure request by ID"""
    return db.query(TaskClosureRequest).filter(
        and_(
            TaskClosureRequest.id == request_id,
            TaskClosureRequest.task_id == task_id
        )
    ).first()

def get_pending_closure_request(
    db: Session,
    task_id: UUID
) -> Optional[TaskClosureRequest]:
    """Get pending closure request for a task"""
    return db.query(TaskClosureRequest).filter(
        and_(
            TaskClosureRequest.task_id == task_id,
            TaskClosureRequest.status == ClosureRequestStatus.pending
        )
    ).first()

def update_closure_request(
    db: Session,
    request_id: UUID,
    task_id: UUID,
    closure_request_update: TaskClosureRequestUpdate,
    reviewed_by: UUID
) -> Optional[TaskClosureRequest]:
    """Update a closure request (approve/reject)"""
    db_request = get_closure_request(db, request_id, task_id)
    if not db_request:
        return None
    
    db_request.status = closure_request_update.status
    db_request.reviewed_by = reviewed_by
    db_request.reviewed_at = datetime.utcnow()
    if closure_request_update.reason:
        db_request.reason = closure_request_update.reason
    
    db.commit()
    db.refresh(db_request)
    return db_request

def get_closure_requests_by_task(
    db: Session,
    task_id: UUID
) -> List[TaskClosureRequest]:
    """Get all closure requests for a task"""
    return db.query(TaskClosureRequest).filter(
        TaskClosureRequest.task_id == task_id
    ).order_by(TaskClosureRequest.created_at.desc()).all()

