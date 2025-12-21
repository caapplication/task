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
    return crud_task.create_task(
        db=db,
        task=task,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
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
    tasks = crud_task.get_tasks_by_agency(
        db=db,
        agency_id=current_agency["id"],
        client_id=client_id,
        assigned_to=assigned_to,
        status=status,
        skip=skip,
        limit=limit
    )
    # Return as list directly (frontend handles both array and {items: []} format)
    return tasks

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
        "priority": task.priority,
        "due_date": task.due_date,
        "target_date": task.target_date,
        "assigned_to": task.assigned_to,
        "tag_id": task.tag_id,
        "document_request": task.document_request,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "total_logged_seconds": total_seconds,
        "is_timer_running_for_me": is_timer_running_for_me,
        "subtasks": subtasks_list
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
    task = crud_task.update_task(
        db=db,
        task_id=task_id,
        task_update=task_update,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

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

