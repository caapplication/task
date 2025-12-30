from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user, get_current_agency
from app.schemas.recurring_task import RecurringTask, RecurringTaskCreate, RecurringTaskUpdate
from app import crud

router = APIRouter(prefix="/recurring-tasks", tags=["recurring-tasks"])

@router.post("/", response_model=RecurringTask, status_code=status.HTTP_201_CREATED)
def create_recurring_task(
    recurring_task: RecurringTaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Create a new recurring task template"""
    return crud.crud_recurring_task.create_recurring_task(
        db=db,
        recurring_task=recurring_task,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )

@router.get("/", response_model=List[RecurringTask])
def list_recurring_tasks(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """List all recurring tasks for the agency"""
    return crud.crud_recurring_task.get_recurring_tasks_by_agency(
        db=db,
        agency_id=current_agency["id"],
        is_active=is_active,
        skip=skip,
        limit=limit
    )

@router.get("/{recurring_task_id}", response_model=RecurringTask)
def get_recurring_task(
    recurring_task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Get a specific recurring task"""
    recurring_task = crud.crud_recurring_task.get_recurring_task(
        db=db,
        recurring_task_id=recurring_task_id,
        agency_id=current_agency["id"]
    )
    if not recurring_task:
        raise HTTPException(status_code=404, detail="Recurring task not found")
    return recurring_task

@router.patch("/{recurring_task_id}", response_model=RecurringTask)
def update_recurring_task(
    recurring_task_id: UUID,
    recurring_task_update: RecurringTaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Update a recurring task"""
    recurring_task = crud.crud_recurring_task.update_recurring_task(
        db=db,
        recurring_task_id=recurring_task_id,
        recurring_task_update=recurring_task_update,
        agency_id=current_agency["id"]
    )
    if not recurring_task:
        raise HTTPException(status_code=404, detail="Recurring task not found")
    return recurring_task

@router.delete("/{recurring_task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_task(
    recurring_task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Delete a recurring task"""
    success = crud.crud_recurring_task.delete_recurring_task(
        db=db,
        recurring_task_id=recurring_task_id,
        agency_id=current_agency["id"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Recurring task not found")

