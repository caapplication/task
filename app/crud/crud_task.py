from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict

from app.models.task import Task, TaskStatus
from app.models.activity_log import ActivityLog
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.activity_log import ActivityLogBase

def convert_uuid_to_str(obj: Any) -> Any:
    """Recursively convert UUID objects to strings for JSON serialization"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_uuid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_uuid_to_str(item) for item in obj]
    return obj

def get_next_task_number(db: Session, agency_id: UUID) -> int:
    """Get the next sequential task number for an agency"""
    max_task_number = db.query(func.max(Task.task_number)).filter(
        Task.agency_id == agency_id
    ).scalar()
    if max_task_number is None:
        return 1
    return max_task_number + 1


def create_task(db: Session, task: TaskCreate, agency_id: UUID, user_id: UUID) -> Task:
    # Exclude recurring task fields and JSON fields from task_data
    task_data = task.model_dump(exclude={
        "document_request", 
        "checklist",
        "is_recurring",
        "recurrence_frequency",
        "recurrence_day_of_week",
        "recurrence_day_of_month",
        "recurrence_start_date"
    })
    document_request = convert_uuid_to_str(task.document_request.model_dump()) if task.document_request else None
    checklist = convert_uuid_to_str(task.checklist.model_dump()) if task.checklist else None
    
    # Get next task number
    task_number = get_next_task_number(db, agency_id)
    
    db_task = Task(
        **task_data,
        agency_id=agency_id,
        task_number=task_number,
        created_by=user_id,
        created_by_name=None,  # Will be set by router with user context
        document_request=document_request,
        checklist=checklist,
        status=TaskStatus.pending
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Create activity log
    activity_log = ActivityLog(
        task_id=db_task.id,
        user_id=user_id,
        action=f"Task created: {db_task.title}",
        details=f"Task '{db_task.title}' was created",
        event_type="task_created",
        to_value={"title": db_task.title, "status": db_task.status.value}
    )
    db.add(activity_log)
    db.commit()
    
    return db_task

def get_task(db: Session, task_id: UUID, agency_id: UUID) -> Optional[Task]:
    return db.query(Task).options(
        joinedload(Task.subtasks),
        joinedload(Task.timers),
        joinedload(Task.activity_logs),
        joinedload(Task.stage)  # Load stage relationship
    ).filter(
        and_(Task.id == task_id, Task.agency_id == agency_id)
    ).first()

def get_tasks_by_agency(
    db: Session,
    agency_id: UUID,
    client_id: Optional[UUID] = None,
    assigned_to: Optional[UUID] = None,
    status: Optional[TaskStatus] = None,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[UUID] = None  # Include tasks where user is a collaborator
) -> List[Task]:
    from app.models.task_collaborator import TaskCollaborator
    from sqlalchemy import or_
    
    query = db.query(Task).options(
        joinedload(Task.stage)  # Load stage relationship for Kanban view
    ).filter(Task.agency_id == agency_id)
    
    if client_id:
        query = query.filter(Task.client_id == client_id)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if status:
        query = query.filter(Task.status == status)
    
    # If user_id is provided, include tasks where user is assigned OR is a collaborator OR user created the task
    # This ensures users see tasks they're involved with, but we don't restrict to only those
    # The collaborator feature adds visibility, it doesn't restrict it
    # Note: We show all tasks by default - collaborators can see tasks they're added to
    # This filter is only applied when explicitly needed (e.g., "My Tasks" view)
    if user_id and assigned_to is None:
        # Only apply collaborator filter if we want to show user's tasks
        # For now, show all tasks - collaborators will see tasks they're added to via access control
        pass  # Removed filter to show all tasks
    
    return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

def update_task(
    db: Session,
    task_id: UUID,
    task_update: TaskUpdate,
    agency_id: UUID,
    user_id: UUID
) -> Optional[Task]:
    db_task = get_task(db, task_id, agency_id)
    if not db_task:
        return None
    
    # Track changes for activity log
    changes = []
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Handle document_request separately
    if "document_request" in update_data:
        document_request = update_data.pop("document_request")
        if document_request:
            if hasattr(document_request, 'model_dump'):
                db_task.document_request = convert_uuid_to_str(document_request.model_dump())
            else:
                db_task.document_request = convert_uuid_to_str(document_request)
        else:
            db_task.document_request = None
    
    # Handle checklist separately
    if "checklist" in update_data:
        old_checklist = db_task.checklist
        checklist = update_data.pop("checklist")
        if checklist:
            if hasattr(checklist, 'model_dump'):
                new_checklist = convert_uuid_to_str(checklist.model_dump())
            else:
                new_checklist = convert_uuid_to_str(checklist)
            db_task.checklist = new_checklist
            
            # Log checklist changes
            if old_checklist != new_checklist:
                # Compare items to detect specific changes
                old_items = old_checklist.get('items', []) if isinstance(old_checklist, dict) else []
                new_items = new_checklist.get('items', []) if isinstance(new_checklist, dict) else []
                
                # Find completed/uncompleted items
                old_completed = {item.get('name'): item.get('is_completed', False) for item in old_items if isinstance(item, dict)}
                new_completed = {item.get('name'): item.get('is_completed', False) for item in new_items if isinstance(item, dict)}
                
                checklist_changes = []
                for item_name in set(list(old_completed.keys()) + list(new_completed.keys())):
                    old_status = old_completed.get(item_name, False)
                    new_status = new_completed.get(item_name, False)
                    if old_status != new_status:
                        checklist_changes.append(f"{item_name}: {'completed' if new_status else 'uncompleted'}")
                
                if checklist_changes:
                    activity_log = ActivityLog(
                        task_id=db_task.id,
                        user_id=user_id,
                        action="Checklist updated",
                        details=f"Checklist items changed: {', '.join(checklist_changes)}",
                        event_type="checklist_updated",
                        from_value={"checklist": old_checklist},
                        to_value={"checklist": new_checklist}
                    )
                    db.add(activity_log)
        else:
            db_task.checklist = None
            if old_checklist:
                activity_log = ActivityLog(
                    task_id=db_task.id,
                    user_id=user_id,
                    action="Checklist removed",
                    details="Checklist was removed from the task",
                    event_type="checklist_removed",
                    from_value={"checklist": old_checklist}
                )
                db.add(activity_log)
    
    for key, value in update_data.items():
        if value is not None:
            old_value = getattr(db_task, key)
            if old_value != value:
                changes.append({
                    "field": key,
                    "from": str(old_value) if old_value is not None else None,
                    "to": str(value) if value is not None else None
                })
                setattr(db_task, key, value)
    
    # Set updated_by and updated_at
    db_task.updated_by = user_id
    db_task.updated_by_name = None  # Will be set by router with user context
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    
    # Create activity log for changes
    if changes:
        change_details = ", ".join([f"{c['field']}: {c['from']} → {c['to']}" for c in changes])
        activity_log = ActivityLog(
            task_id=db_task.id,
            user_id=user_id,
            action=f"Task updated: {db_task.title}",
            details=f"Changes: {change_details}",
            event_type="task_updated",
            from_value={c["field"]: c["from"] for c in changes},
            to_value={c["field"]: c["to"] for c in changes}
        )
        db.add(activity_log)
        db.commit()
    
    return db_task

def delete_task(db: Session, task_id: UUID, agency_id: UUID, user_id: UUID) -> bool:
    db_task = get_task(db, task_id, agency_id)
    if not db_task:
        return False
    
    # Create activity log before deletion
    activity_log = ActivityLog(
        task_id=db_task.id,
        user_id=user_id,
        action=f"Task deleted: {db_task.title}",
        details=f"Task '{db_task.title}' was deleted",
        event_type="task_deleted"
    )
    db.add(activity_log)
    
    db.delete(db_task)
    db.commit()
    return True

