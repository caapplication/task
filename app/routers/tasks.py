from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from fastapi import Request
from app.dependencies import get_current_user, get_current_agency, require_role
from app.crud import crud_task, crud_task_subtask, crud_task_timer, crud_activity_log
from app.schemas.task import TaskCreate, TaskUpdate, Task, TaskListItem
from app.schemas.task_subtask import TaskSubtaskCreate, TaskSubtaskUpdate, TaskSubtask
from app.schemas.task_timer import TaskTimer, ManualTimeEntry
from app.schemas.activity_log import ActivityLog
from app.models.task import TaskStatus

router = APIRouter()

def get_db(request: Request):
    return request.state.db

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
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
            "agency_id": db_task.agency_id,
            "client_id": db_task.client_id,
            "service_id": db_task.service_id,
            "title": db_task.title,
            "description": db_task.description,
            "status": db_task.status,
            "stage_id": db_task.stage_id,
            "priority": db_task.priority,
            "due_date": db_task.due_date,
            "target_date": db_task.target_date,
            "assigned_to": db_task.assigned_to,
            "tag_id": db_task.tag_id,
            "document_request": db_task.document_request,
            "checklist": db_task.checklist,
            "created_by": db_task.created_by,
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
    
    tasks = crud_task.get_tasks_by_agency(
        db=db,
        agency_id=current_agency["id"],
        client_id=client_id,
        assigned_to=assigned_to,
        status=status,
        skip=skip,
        limit=limit
    )
    
    # Serialize tasks with stage information for Kanban view
    task_list = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "client_id": task.client_id,
            "service_id": task.service_id,
            "status": task.status,
            "stage_id": task.stage_id,  # Include stage_id
            "priority": task.priority,
            "due_date": task.due_date,
            "assigned_to": task.assigned_to,
            "tag_id": task.tag_id,
            "created_at": task.created_at,
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
    from datetime import datetime, timezone
    from app.schemas.task import Task as TaskSchema
    
    task = crud_task.get_task(db=db, task_id=task_id, agency_id=current_agency["id"])
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
        "agency_id": task.agency_id,
        "client_id": task.client_id,
        "service_id": task.service_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "stage_id": task.stage_id,
        "priority": task.priority,
        "due_date": task.due_date,
        "target_date": task.target_date,
        "assigned_to": task.assigned_to,
        "tag_id": task.tag_id,
        "document_request": task.document_request,
        "checklist": task.checklist,
        "created_by": task.created_by,
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
        "agency_id": task.agency_id,
        "client_id": task.client_id,
        "service_id": task.service_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "stage_id": task.stage_id,
        "priority": task.priority,
        "due_date": task.due_date,
        "target_date": task.target_date,
        "assigned_to": task.assigned_to,
        "tag_id": task.tag_id,
        "document_request": task.document_request,
        "checklist": task.checklist,
        "created_by": task.created_by,
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

