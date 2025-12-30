"""
Service to automatically create tasks from recurring task templates.
This should be run as a background job (e.g., via cron, celery, or APScheduler).
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List
import logging

from app.database import SessionLocal
from app import crud
from app.schemas.task import TaskCreate, TaskPriority
from app.schemas.task import DocumentRequest as DocumentRequestSchema

logger = logging.getLogger(__name__)

def create_tasks_from_recurring_templates(check_date: date = None) -> int:
    """
    Create tasks from recurring task templates for the given date.
    If no date is provided, uses today's date.
    
    Returns the number of tasks created.
    """
    if check_date is None:
        check_date = date.today()
    
    db: Session = SessionLocal()
    tasks_created = 0
    
    try:
        # Get all active recurring tasks that should create tasks today
        recurring_tasks = crud.crud_recurring_task.get_active_recurring_tasks_due(
            db=db,
            check_date=check_date
        )
        
        logger.info(f"Found {len(recurring_tasks)} recurring tasks due on {check_date}")
        
        for recurring_task in recurring_tasks:
            try:
                # Create task from template
                task_data = create_task_from_recurring_template(recurring_task, check_date)
                
                # Get agency_id and created_by from recurring task
                agency_id = recurring_task.agency_id
                created_by = recurring_task.created_by
                
                # Create the task
                created_task = crud.crud_task.create_task(
                    db=db,
                    task=task_data,
                    agency_id=agency_id,
                    user_id=created_by
                )
                
                # Update last_created_at timestamp
                crud.crud_recurring_task.update_last_created_at(
                    db=db,
                    recurring_task_id=recurring_task.id,
                    created_at=datetime.utcnow()
                )
                
                tasks_created += 1
                logger.info(f"Created task '{created_task.title}' from recurring task '{recurring_task.title}'")
                
            except Exception as e:
                logger.error(f"Error creating task from recurring task {recurring_task.id}: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"Successfully created {tasks_created} tasks from recurring templates")
        
    except Exception as e:
        logger.error(f"Error in create_tasks_from_recurring_templates: {str(e)}")
        db.rollback()
    finally:
        db.close()
    
    return tasks_created

def create_task_from_recurring_template(recurring_task, creation_date: date) -> TaskCreate:
    """Convert a recurring task template into a TaskCreate schema"""
    from app.schemas.recurring_task import RecurringTask
    
    # Calculate due_date and target_date based on offsets
    due_date = None
    if recurring_task.due_date_offset is not None:
        due_date = creation_date + timedelta(days=recurring_task.due_date_offset)
    
    target_date = None
    if recurring_task.target_date_offset is not None:
        target_date = creation_date + timedelta(days=recurring_task.target_date_offset)
    
    # Convert priority string to enum if needed
    priority = None
    if recurring_task.priority:
        try:
            priority = TaskPriority(recurring_task.priority)
        except ValueError:
            priority = None
    
    # Convert document_request JSON to schema if present
    document_request = None
    if recurring_task.document_request:
        try:
            doc_req_data = recurring_task.document_request
            if isinstance(doc_req_data, dict):
                document_request = DocumentRequestSchema(**doc_req_data)
        except Exception as e:
            logger.warning(f"Error parsing document_request for recurring task {recurring_task.id}: {e}")
    
    return TaskCreate(
        title=recurring_task.title,
        description=recurring_task.description,
        client_id=recurring_task.client_id,
        service_id=recurring_task.service_id,
        priority=priority,
        assigned_to=recurring_task.assigned_to,
        tag_id=recurring_task.tag_id,
        document_request=document_request,
        due_date=due_date,
        target_date=target_date
    )

def run_daily_scheduler():
    """Main entry point for daily scheduler - should be called by cron or task scheduler"""
    today = date.today()
    logger.info(f"Running recurring task scheduler for {today}")
    tasks_created = create_tasks_from_recurring_templates(today)
    logger.info(f"Recurring task scheduler completed. Created {tasks_created} tasks.")
    return tasks_created

