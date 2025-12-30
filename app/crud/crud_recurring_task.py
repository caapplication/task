from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional

from app.models.recurring_task import RecurringTask, RecurrenceFrequency
from app.schemas.recurring_task import RecurringTaskCreate, RecurringTaskUpdate

def create_recurring_task(
    db: Session,
    recurring_task: RecurringTaskCreate,
    agency_id: UUID,
    user_id: UUID
) -> RecurringTask:
    """Create a new recurring task template"""
    task_data = recurring_task.model_dump(exclude={"document_request"})
    document_request = recurring_task.document_request.model_dump() if recurring_task.document_request else None
    
    db_recurring_task = RecurringTask(
        **task_data,
        agency_id=agency_id,
        created_by=user_id,
        document_request=document_request
    )
    db.add(db_recurring_task)
    db.commit()
    db.refresh(db_recurring_task)
    
    return db_recurring_task

def get_recurring_task(
    db: Session,
    recurring_task_id: UUID,
    agency_id: UUID
) -> Optional[RecurringTask]:
    """Get a recurring task by ID"""
    return db.query(RecurringTask).filter(
        and_(
            RecurringTask.id == recurring_task_id,
            RecurringTask.agency_id == agency_id
        )
    ).first()

def get_recurring_tasks_by_agency(
    db: Session,
    agency_id: UUID,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[RecurringTask]:
    """Get all recurring tasks for an agency"""
    query = db.query(RecurringTask).filter(RecurringTask.agency_id == agency_id)
    
    if is_active is not None:
        query = query.filter(RecurringTask.is_active == is_active)
    
    return query.order_by(RecurringTask.created_at.desc()).offset(skip).limit(limit).all()

def update_recurring_task(
    db: Session,
    recurring_task_id: UUID,
    recurring_task_update: RecurringTaskUpdate,
    agency_id: UUID
) -> Optional[RecurringTask]:
    """Update a recurring task"""
    db_recurring_task = get_recurring_task(db, recurring_task_id, agency_id)
    if not db_recurring_task:
        return None
    
    update_data = recurring_task_update.model_dump(exclude_unset=True)
    
    # Handle document_request separately
    if "document_request" in update_data:
        document_request = update_data.pop("document_request")
        if document_request:
            db_recurring_task.document_request = document_request.model_dump() if hasattr(document_request, 'model_dump') else document_request
        else:
            db_recurring_task.document_request = None
    
    for key, value in update_data.items():
        if value is not None:
            setattr(db_recurring_task, key, value)
    
    db_recurring_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_recurring_task)
    
    return db_recurring_task

def delete_recurring_task(
    db: Session,
    recurring_task_id: UUID,
    agency_id: UUID
) -> bool:
    """Delete a recurring task"""
    db_recurring_task = get_recurring_task(db, recurring_task_id, agency_id)
    if not db_recurring_task:
        return False
    
    db.delete(db_recurring_task)
    db.commit()
    return True

def get_active_recurring_tasks_due(
    db: Session,
    check_date: date
) -> List[RecurringTask]:
    """Get all active recurring tasks that should create tasks on the given date"""
    from datetime import timedelta
    
    active_tasks = db.query(RecurringTask).filter(
        RecurringTask.is_active == True,
        RecurringTask.start_date <= check_date,
        or_(
            RecurringTask.end_date.is_(None),
            RecurringTask.end_date >= check_date
        )
    ).all()
    
    due_tasks = []
    for task in active_tasks:
        if should_create_task_today(task, check_date):
            due_tasks.append(task)
    
    return due_tasks

def should_create_task_today(recurring_task: RecurringTask, check_date: date) -> bool:
    """Determine if a task should be created on the given date based on recurrence pattern"""
    from datetime import timedelta
    
    # Check if we've already created a task today
    if recurring_task.last_created_at:
        last_created = recurring_task.last_created_at.date()
        if last_created == check_date:
            return False
    
    # Check if start_date has passed
    if check_date < recurring_task.start_date:
        return False
    
    # Check if end_date has passed
    if recurring_task.end_date and check_date > recurring_task.end_date:
        return False
    
    # Calculate days since start
    days_since_start = (check_date - recurring_task.start_date).days
    
    if recurring_task.frequency == RecurrenceFrequency.daily:
        return days_since_start % recurring_task.interval == 0
    
    elif recurring_task.frequency == RecurrenceFrequency.weekly:
        if days_since_start % (recurring_task.interval * 7) != 0:
            return False
        # Check day of week if specified
        if recurring_task.day_of_week is not None:
            return check_date.weekday() == recurring_task.day_of_week
        return True
    
    elif recurring_task.frequency == RecurrenceFrequency.monthly:
        # Check if it's the right day of month
        if recurring_task.day_of_month is not None:
            if check_date.day != recurring_task.day_of_month:
                return False
        elif recurring_task.week_of_month is not None and recurring_task.day_of_week is not None:
            # Nth weekday of month (e.g., first Monday)
            week_num = (check_date.day - 1) // 7 + 1
            if week_num != recurring_task.week_of_month or check_date.weekday() != recurring_task.day_of_week:
                return False
        
        # Check if enough months have passed
        months_since_start = (check_date.year - recurring_task.start_date.year) * 12 + \
                            (check_date.month - recurring_task.start_date.month)
        return months_since_start % recurring_task.interval == 0
    
    elif recurring_task.frequency == RecurrenceFrequency.yearly:
        # Check if it's the same month and day
        if check_date.month != recurring_task.start_date.month or \
           check_date.day != recurring_task.start_date.day:
            return False
        # Check if enough years have passed
        years_since_start = check_date.year - recurring_task.start_date.year
        return years_since_start % recurring_task.interval == 0
    
    return False

def update_last_created_at(
    db: Session,
    recurring_task_id: UUID,
    created_at: datetime
) -> None:
    """Update the last_created_at timestamp for a recurring task"""
    db_recurring_task = db.query(RecurringTask).filter(
        RecurringTask.id == recurring_task_id
    ).first()
    if db_recurring_task:
        db_recurring_task.last_created_at = created_at
        db.commit()

