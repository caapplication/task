from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import requests
import os

from fastapi import Request
from app.dependencies import get_current_user, get_current_agency, require_role
from app.crud import crud_task, crud_task_subtask, crud_task_timer, crud_activity_log, crud_task_collaborator, crud_task_comment_read, crud_task_closure_request
from app.schemas.task import TaskCreate, TaskUpdate, Task, TaskListItem
from app.schemas.task_subtask import TaskSubtaskCreate, TaskSubtaskUpdate, TaskSubtask
from app.schemas.task_timer import TaskTimer, ManualTimeEntry
from app.schemas.activity_log import ActivityLog
from app.schemas.task_collaborator import TaskCollaborator, TaskCollaboratorCreate
from app.schemas.task_closure_request import TaskClosureRequest, TaskClosureRequestCreate, TaskClosureRequestUpdate, ClosureRequestStatus
from app.models.task import TaskStatus
from app import config

router = APIRouter()
http_bearer = HTTPBearer()

def get_db(request: Request):
    return request.state.db

def fetch_user_info_from_login_service(user_id: UUID, token: str = None) -> dict:
    """Fetch user name and role from Login service"""
    try:
        login_service_url = config.API_URL or os.getenv("API_URL", "http://127.0.0.1:8001")
        headers = {
            "accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Call profile endpoint to get user info
        profile_url = f"{login_service_url}/profile/" if not login_service_url.endswith('/') else f"{login_service_url}profile/"
        response = requests.get(profile_url, headers=headers, timeout=5)
        if response.status_code == 200:
            user_data = response.json()
            return {
                "name": user_data.get("name") or user_data.get("email", "Unknown"),
                "role": user_data.get("role") or "N/A"
            }
        return {"name": None, "role": None}
    except Exception as e:
        print(f"Error fetching user info from Login service: {e}")
        return {"name": None, "role": None}

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    token: str = Depends(http_bearer),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    from app.schemas.task import Task as TaskSchema
    from app.schemas.recurring_task import RecurringTaskCreate, RecurrenceFrequency
    import traceback
    
    try:
        # Create the regular task first
        db_task = crud_task.create_task(
            db=db,
            task=task,
            agency_id=current_agency["id"],
            user_id=UUID(current_user["id"])
        )
        
        # Fetch creator's name and role from Login service
        token_str = token.credentials if hasattr(token, 'credentials') else None
        creator_info = fetch_user_info_from_login_service(
            UUID(current_user["id"]), 
            token_str
        )
        db_task.created_by_name = creator_info.get("name") or current_user.get("name") or current_user.get("email", "Unknown")
        db_task.created_by_role = creator_info.get("role") or current_user.get("role") or "N/A"
        db.commit()
        db.refresh(db_task)
        
        # If this is a recurring task, create the recurring task template
        if task.is_recurring and task.recurrence_frequency and task.recurrence_start_date:
            from app import crud
            
            # Map frequency string to enum
            frequency_map = {
                'weekly': RecurrenceFrequency.weekly,
                'monthly': RecurrenceFrequency.monthly
            }
            
            recurring_task_data = RecurringTaskCreate(
                title=task.title,
                description=task.description,
                client_id=task.client_id,
                service_id=task.service_id,
                priority=task.priority,
                assigned_to=task.assigned_to,
                tag_id=task.tag_id,
                document_request=task.document_request,
                frequency=frequency_map.get(task.recurrence_frequency, RecurrenceFrequency.weekly),
                interval=1,  # Every week/month
                start_date=task.recurrence_start_date,
                end_date=None,
                day_of_week=task.recurrence_day_of_week if task.recurrence_frequency == 'weekly' else None,
                day_of_month=task.recurrence_day_of_month if task.recurrence_frequency == 'monthly' else None,
                week_of_month=None,
                due_date_offset=0,
                target_date_offset=None,
                is_active=True
            )
            
            # Create the recurring task
            crud.crud_recurring_task.create_recurring_task(
                db=db,
                recurring_task=recurring_task_data,
                agency_id=current_agency["id"],
                user_id=UUID(current_user["id"])
            )
        
        # Serialize the task properly like get_task does
        subtasks_list = []
        if db_task.subtasks:
            for subtask in db_task.subtasks:
                subtasks_list.append({
                    "id": subtask.id,
                    "task_id": subtask.task_id,
                    "title": subtask.title,
                    "description": subtask.description,
                    "is_completed": subtask.is_completed,
                    "sort_order": subtask.sort_order,
                    "created_at": subtask.created_at,
                    "updated_at": subtask.updated_at
                })
        
        task_dict = {
            "id": db_task.id,
            "task_number": db_task.task_number,
            "agency_id": db_task.agency_id,
            "client_id": db_task.client_id,
            "service_id": db_task.service_id,
            "title": db_task.title,
            "description": db_task.description,
            "status": db_task.status,
            "stage_id": db_task.stage_id,
            "priority": db_task.priority,
            "due_date": db_task.due_date,
            "due_time": db_task.due_time,
            "target_date": db_task.target_date,
            "assigned_to": db_task.assigned_to,
            "tag_id": db_task.tag_id,
            "document_request": db_task.document_request,
            "checklist": db_task.checklist,
            "created_by": db_task.created_by,
            "created_by_name": db_task.created_by_name,
            "created_by_role": db_task.created_by_role,
            "updated_by": db_task.updated_by,
            "updated_by_name": db_task.updated_by_name,
            "updated_by_role": db_task.updated_by_role,
            "created_at": db_task.created_at,
            "updated_at": db_task.updated_at,
            "total_logged_seconds": 0,
            "is_timer_running_for_me": False,
            "subtasks": subtasks_list
        }
        
        # Include stage object if stage_id is set (load it if needed)
        if db_task.stage_id:
            # Try to access stage, if not loaded, query it
            if db_task.stage:
                task_dict["stage"] = {
                    "id": db_task.stage.id,
                    "name": db_task.stage.name,
                    "color": db_task.stage.color,
                    "description": db_task.stage.description
                }
            else:
                # Load stage if not already loaded
                from app.models.task_stage import TaskStage
                stage = db.query(TaskStage).filter(TaskStage.id == db_task.stage_id).first()
                if stage:
                    task_dict["stage"] = {
                        "id": stage.id,
                        "name": stage.name,
                        "color": stage.color,
                        "description": stage.description
                    }
        
        return TaskSchema(**task_dict)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error creating task: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}. Please check server logs for details."
        )

@router.get("/", response_model=List[TaskListItem])
def list_tasks(
    client_id: Optional[UUID] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    from app.schemas.task import TaskListItem
    
    # Show all tasks in the agency by default
    # Collaborators can access tasks they're added to via the task detail endpoint
    # Don't filter by user_id here - show all tasks for the agency
    tasks = crud_task.get_tasks_by_agency(
        db=db,
        agency_id=current_agency["id"],
        client_id=client_id,
        assigned_to=assigned_to,
        status=status,
        skip=skip,
        limit=limit,
        user_id=None  # Don't filter by user - show all tasks
    )
    
    # Serialize tasks with stage information for Kanban view
    task_list = []
    current_user_id = UUID(current_user["id"]) if current_user.get("id") else None
    
    for task in tasks:
        # Check if user has unread messages for this task
        has_unread = False
        if current_user_id:
            has_unread = crud_task_comment_read.has_unread_comments(
                db=db,
                task_id=task.id,
                user_id=current_user_id
            )
        
        task_dict = {
            "id": task.id,
            "task_number": task.task_number,
            "title": task.title,
            "client_id": task.client_id,
            "service_id": task.service_id,
            "status": task.status,
            "stage_id": task.stage_id,  # Include stage_id
            "priority": task.priority,
            "due_date": task.due_date,
            "due_time": task.due_time,
            "assigned_to": task.assigned_to,
            "tag_id": task.tag_id,
            "created_by": task.created_by,
            "created_by_name": task.created_by_name,
            "created_by_role": task.created_by_role,
            "updated_by": task.updated_by,
            "updated_by_name": task.updated_by_name,
            "updated_by_role": task.updated_by_role,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "has_unread_messages": has_unread,
        }
        
        # Include stage object if loaded
        if task.stage:
            task_dict["stage"] = {
                "id": task.stage.id,
                "name": task.stage.name,
                "color": task.stage.color,
                "description": task.stage.description
            }
        
        task_list.append(TaskListItem(**task_dict))
    
    return task_list

@router.get("/{task_id}", response_model=Task)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    from app.models.task_timer import TaskTimer
    from app.models.task import Task
    from sqlalchemy.orm import joinedload
    from datetime import datetime, timezone
    from app.schemas.task import Task as TaskSchema
    
    # Load task with collaborators relationship
    task = db.query(Task).options(
        joinedload(Task.collaborators)
    ).filter(
        Task.id == task_id,
        Task.agency_id == current_agency["id"]
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Calculate total logged seconds from all timers
    all_timers = db.query(TaskTimer).filter(TaskTimer.task_id == task_id).all()
    total_seconds = 0
    for timer in all_timers:
        if timer.is_active and timer.start_time:
            # Add current running time for active timers (use timezone-aware datetime)
            now = datetime.now(timezone.utc)
            elapsed = int((now - timer.start_time).total_seconds())
            total_seconds += elapsed
        else:
            # Add stored duration for stopped timers
            total_seconds += timer.duration_seconds or 0
    
    # Check if current user has an active timer
    user_id_str = current_user.get("id")
    is_timer_running_for_me = False
    if user_id_str:
        try:
            user_id = UUID(user_id_str)
            active_timer = db.query(TaskTimer).filter(
                TaskTimer.task_id == task_id,
                TaskTimer.user_id == user_id,
                TaskTimer.is_active == True
            ).first()
            is_timer_running_for_me = active_timer is not None
        except (ValueError, TypeError):
            pass
    
    # Serialize subtasks properly
    from app.schemas.task_subtask import TaskSubtask as TaskSubtaskSchema
    
    subtasks_list = []
    if task.subtasks:
        for subtask in task.subtasks:
            subtasks_list.append({
                "id": subtask.id,
                "task_id": subtask.task_id,
                "title": subtask.title,
                "description": subtask.description,
                "is_completed": subtask.is_completed,
                "sort_order": subtask.sort_order,
                "created_at": subtask.created_at,
                "updated_at": subtask.updated_at
            })
    
    task_dict = {
        "id": task.id,
        "task_number": task.task_number,
        "agency_id": task.agency_id,
        "client_id": task.client_id,
        "service_id": task.service_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "stage_id": task.stage_id,
        "priority": task.priority,
        "due_date": task.due_date,
        "due_time": task.due_time,
        "target_date": task.target_date,
        "assigned_to": task.assigned_to,
        "tag_id": task.tag_id,
        "document_request": task.document_request,
        "checklist": task.checklist,
        "created_by": task.created_by,
        "created_by_name": task.created_by_name,
        "created_by_role": task.created_by_role,
        "updated_by": task.updated_by,
        "updated_by_name": task.updated_by_name,
        "updated_by_role": task.updated_by_role,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "total_logged_seconds": total_seconds,
        "is_timer_running_for_me": is_timer_running_for_me,
        "subtasks": subtasks_list
    }
    
    # Include stage object if loaded
    if task.stage:
        task_dict["stage"] = {
            "id": task.stage.id,
            "name": task.stage.name,
            "color": task.stage.color,
            "description": task.stage.description
        }
    
    return TaskSchema(**task_dict)

@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(http_bearer),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    from app.schemas.task import Task as TaskSchema
    from app.models.task_timer import TaskTimer
    from datetime import datetime, timezone
    
    task = crud_task.update_task(
        db=db,
        task_id=task_id,
        task_update=task_update,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Fetch updater's name and role from Login service
    token_str = token.credentials if hasattr(token, 'credentials') else None
    updater_info = fetch_user_info_from_login_service(
        UUID(current_user["id"]), 
        token_str
    )
    task.updated_by_name = updater_info.get("name") or current_user.get("name") or current_user.get("email", "Unknown")
    task.updated_by_role = updater_info.get("role") or current_user.get("role") or "N/A"
    db.commit()
    db.refresh(task)
    
    # Reload task with relationships
    db.refresh(task)
    if task.stage_id and not task.stage:
        from app.models.task_stage import TaskStage
        task.stage = db.query(TaskStage).filter(TaskStage.id == task.stage_id).first()
    
    # Calculate total logged seconds
    all_timers = db.query(TaskTimer).filter(TaskTimer.task_id == task_id).all()
    total_seconds = 0
    for timer in all_timers:
        if timer.is_active and timer.start_time:
            now = datetime.now(timezone.utc)
            elapsed = int((now - timer.start_time).total_seconds())
            total_seconds += elapsed
        else:
            total_seconds += timer.duration_seconds or 0
    
    # Check if current user has an active timer
    user_id_str = current_user.get("id")
    is_timer_running_for_me = False
    if user_id_str:
        try:
            user_id = UUID(user_id_str)
            active_timer = db.query(TaskTimer).filter(
                TaskTimer.task_id == task_id,
                TaskTimer.user_id == user_id,
                TaskTimer.is_active == True
            ).first()
            is_timer_running_for_me = active_timer is not None
        except (ValueError, TypeError):
            pass
    
    # Serialize subtasks
    subtasks_list = []
    if task.subtasks:
        for subtask in task.subtasks:
            subtasks_list.append({
                "id": subtask.id,
                "task_id": subtask.task_id,
                "title": subtask.title,
                "description": subtask.description,
                "is_completed": subtask.is_completed,
                "sort_order": subtask.sort_order,
                "created_at": subtask.created_at,
                "updated_at": subtask.updated_at
            })
    
    # Serialize task with stage information
    task_dict = {
        "id": task.id,
        "task_number": task.task_number,
        "agency_id": task.agency_id,
        "client_id": task.client_id,
        "service_id": task.service_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "stage_id": task.stage_id,
        "priority": task.priority,
        "due_date": task.due_date,
        "due_time": task.due_time,
        "target_date": task.target_date,
        "assigned_to": task.assigned_to,
        "tag_id": task.tag_id,
        "document_request": task.document_request,
        "checklist": task.checklist,
        "created_by": task.created_by,
        "created_by_name": task.created_by_name,
        "created_by_role": task.created_by_role,
        "updated_by": task.updated_by,
        "updated_by_name": task.updated_by_name,
        "updated_by_role": task.updated_by_role,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "total_logged_seconds": total_seconds,
        "is_timer_running_for_me": is_timer_running_for_me,
        "subtasks": subtasks_list
    }
    
    # Include stage object if loaded
    if task.stage:
        task_dict["stage"] = {
            "id": task.stage.id,
            "name": task.stage.name,
            "color": task.stage.color,
            "description": task.stage.description
        }
    
    return TaskSchema(**task_dict)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    success = crud_task.delete_task(
        db=db,
        task_id=task_id,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

@router.get("/{task_id}/history", response_model=List[ActivityLog])
def get_task_history(
    task_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    # Verify task exists
    task = crud_task.get_task(db=db, task_id=task_id, agency_id=current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud_activity_log.get_activity_logs_by_task(
        db=db,
        task_id=task_id,
        agency_id=current_agency["id"],
        skip=skip,
        limit=limit
    )

@router.post("/{task_id}/timer/start", response_model=TaskTimer)
def start_task_timer(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    timer = crud_task_timer.start_timer(
        db=db,
        task_id=task_id,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not timer:
        raise HTTPException(status_code=404, detail="Task not found")
    return timer

@router.post("/{task_id}/timer/stop", response_model=TaskTimer)
def stop_task_timer(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    timer = crud_task_timer.stop_timer(
        db=db,
        task_id=task_id,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not timer:
        raise HTTPException(status_code=404, detail="Task not found or no active timer")
    return timer

@router.post("/{task_id}/timer/manual", response_model=TaskTimer)
def add_manual_time(
    task_id: UUID,
    time_entry: ManualTimeEntry,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    timer = crud_task_timer.add_manual_time(
        db=db,
        task_id=task_id,
        time_entry=time_entry,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not timer:
        raise HTTPException(status_code=404, detail="Task not found")
    return timer

@router.post("/{task_id}/subtasks", response_model=TaskSubtask, status_code=status.HTTP_201_CREATED)
def create_subtask(
    task_id: UUID,
    subtask: TaskSubtaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    db_subtask = crud_task_subtask.create_subtask(
        db=db,
        task_id=task_id,
        subtask=subtask,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not db_subtask:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_subtask

@router.get("/{task_id}/subtasks", response_model=List[TaskSubtask])
def get_subtasks(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    # Verify task exists
    task = crud_task.get_task(db=db, task_id=task_id, agency_id=current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud_task_subtask.get_subtasks_by_task(
        db=db,
        task_id=task_id,
        agency_id=current_agency["id"]
    )

@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=TaskSubtask)
def update_subtask(
    task_id: UUID,
    subtask_id: UUID,
    subtask_update: TaskSubtaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    db_subtask = crud_task_subtask.update_subtask(
        db=db,
        subtask_id=subtask_id,
        task_id=task_id,
        subtask_update=subtask_update,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not db_subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return db_subtask

@router.delete("/{task_id}/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subtask(
    task_id: UUID,
    subtask_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    success = crud_task_subtask.delete_subtask(
        db=db,
        subtask_id=subtask_id,
        task_id=task_id,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not success:
        raise HTTPException(status_code=404, detail="Subtask not found")

# Collaborator endpoints
@router.post("/{task_id}/collaborators", response_model=TaskCollaborator, status_code=status.HTTP_201_CREATED)
def add_task_collaborator(
    task_id: UUID,
    collaborator: TaskCollaboratorCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Add a collaborator to a task"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Don't allow adding the assigned user as collaborator (they're already assigned)
    if task.assigned_to == collaborator.user_id:
        raise HTTPException(status_code=400, detail="User is already assigned to this task")
    
    # Don't allow adding the creator as collaborator
    if task.created_by == collaborator.user_id:
        raise HTTPException(status_code=400, detail="User is the creator of this task")
    
    return crud_task_collaborator.add_collaborator(
        db=db,
        task_id=task_id,
        user_id=collaborator.user_id,
        added_by=UUID(current_user["id"])
    )

@router.delete("/{task_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task_collaborator(
    task_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Remove a collaborator from a task"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    deleted = crud_task_collaborator.remove_collaborator(
        db=db,
        task_id=task_id,
        user_id=user_id,
        removed_by=UUID(current_user["id"])
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    
    return None

@router.get("/{task_id}/collaborators", response_model=List[TaskCollaborator])
def get_task_collaborators(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Get all collaborators for a task"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud_task_collaborator.get_task_collaborators(db=db, task_id=task_id)

# Task Closure Request Endpoints
@router.post("/{task_id}/closure-request", response_model=TaskClosureRequest, status_code=status.HTTP_201_CREATED)
def request_task_closure(
    task_id: UUID,
    closure_request: TaskClosureRequestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Request to close a task (can only be done by assigned user)"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is assigned to this task
    if task.assigned_to != UUID(current_user["id"]):
        raise HTTPException(
            status_code=403, 
            detail="Only the assigned user can request to close this task"
        )
    
    # Check if task is already completed
    if task.status == TaskStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Task is already completed"
        )
    
    # Create closure request
    closure_request.task_id = task_id
    db_request = crud_task_closure_request.create_closure_request(
        db=db,
        closure_request=closure_request,
        requested_by=UUID(current_user["id"])
    )
    
    # Create activity log
    crud_activity_log.create_activity_log(
        db=db,
        task_id=task_id,
        action="closure_requested",
        user_id=UUID(current_user["id"]),
        details={"request_id": str(db_request.id)}
    )
    
    # Emit notification to task creator (if different from requester)
    try:
        from app.socketio_manager import emit_task_notification
        import asyncio
        if task.created_by != UUID(current_user["id"]):
            asyncio.create_task(emit_task_notification(
                str(task.created_by),
                {
                    "type": "closure_request",
                    "task_id": str(task_id),
                    "task_title": task.title,
                    "requested_by": current_user.get("name") or current_user.get("email", "Unknown"),
                    "request_id": str(db_request.id)
                }
            ))
    except Exception as e:
        print(f"Socket.IO notification error: {e}")
    
    return db_request

@router.patch("/{task_id}/closure-request/{request_id}", response_model=TaskClosureRequest)
def review_closure_request(
    task_id: UUID,
    request_id: UUID,
    closure_request_update: TaskClosureRequestUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Approve or reject a closure request (can only be done by task creator)"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is the task creator
    if task.created_by != UUID(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="Only the task creator can approve or reject closure requests"
        )
    
    # Get the closure request
    db_request = crud_task_closure_request.get_closure_request(db, request_id, task_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Closure request not found")
    
    # Check if request is already reviewed
    if db_request.status != ClosureRequestStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=f"Closure request has already been {db_request.status.value}"
        )
    
    # Update closure request
    updated_request = crud_task_closure_request.update_closure_request(
        db=db,
        request_id=request_id,
        task_id=task_id,
        closure_request_update=closure_request_update,
        reviewed_by=UUID(current_user["id"])
    )
    
    # If approved, update task status to completed
    if closure_request_update.status == ClosureRequestStatus.approved:
        from app.schemas.task import TaskUpdate
        task_update = TaskUpdate(status=TaskStatus.completed)
        crud_task.update_task(
            db=db,
            task_id=task_id,
            task_update=task_update,
            agency_id=current_agency["id"],
            user_id=UUID(current_user["id"])
        )
        
        # Create activity log
        crud_activity_log.create_activity_log(
            db=db,
            task_id=task_id,
            action="task_closed",
            user_id=UUID(current_user["id"]),
            details={"closure_request_id": str(request_id), "approved_by": current_user.get("name") or current_user.get("email", "Unknown")}
        )
        
        # Emit notification to requester
        try:
            from app.socketio_manager import emit_task_notification
            import asyncio
            asyncio.create_task(emit_task_notification(
                str(db_request.requested_by),
                {
                    "type": "closure_approved",
                    "task_id": str(task_id),
                    "task_title": task.title,
                    "reviewed_by": current_user.get("name") or current_user.get("email", "Unknown")
                }
            ))
        except Exception as e:
            print(f"Socket.IO notification error: {e}")
    else:
        # Create activity log for rejection
        crud_activity_log.create_activity_log(
            db=db,
            task_id=task_id,
            action="closure_rejected",
            user_id=UUID(current_user["id"]),
            details={"closure_request_id": str(request_id), "rejected_by": current_user.get("name") or current_user.get("email", "Unknown")}
        )
        
        # Emit notification to requester
        try:
            from app.socketio_manager import emit_task_notification
            import asyncio
            asyncio.create_task(emit_task_notification(
                str(db_request.requested_by),
                {
                    "type": "closure_rejected",
                    "task_id": str(task_id),
                    "task_title": task.title,
                    "reviewed_by": current_user.get("name") or current_user.get("email", "Unknown")
                }
            ))
        except Exception as e:
            print(f"Socket.IO notification error: {e}")
    
    return updated_request

@router.get("/{task_id}/closure-request", response_model=Optional[TaskClosureRequest])
def get_closure_request(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Get pending closure request for a task"""
    # Verify task exists and belongs to agency
    task = crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud_task_closure_request.get_pending_closure_request(db, task_id)

