from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from fastapi import Request
from app.dependencies import get_current_user, get_current_agency
from app.crud import crud_task_stage
from app.schemas.task_stage import TaskStageCreate, TaskStageUpdate, TaskStage

router = APIRouter()

def get_db(request: Request):
    return request.state.db

@router.post("/", response_model=TaskStage, status_code=status.HTTP_201_CREATED)
def create_stage(
    stage: TaskStageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    return crud_task_stage.create_stage(
        db=db,
        stage=stage,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )

@router.get("/", response_model=List[TaskStage])
def list_stages(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    # Initialize default stages if none exist
    stages = crud_task_stage.get_stages_by_agency(db, current_agency["id"])
    if not stages:
        stages = crud_task_stage.initialize_default_stages(
            db=db,
            agency_id=current_agency["id"],
            user_id=UUID(current_user["id"])
        )
    return stages

@router.get("/{stage_id}", response_model=TaskStage)
def get_stage(
    stage_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    stage = crud_task_stage.get_stage(db, stage_id, current_agency["id"])
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage

@router.patch("/{stage_id}", response_model=TaskStage)
def update_stage(
    stage_id: UUID,
    stage_update: TaskStageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    stage = crud_task_stage.update_stage(
        db=db,
        stage_id=stage_id,
        stage_update=stage_update,
        agency_id=current_agency["id"]
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage

@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(
    stage_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    success = crud_task_stage.delete_stage(
        db=db,
        stage_id=stage_id,
        agency_id=current_agency["id"],
        user_id=UUID(current_user["id"])
    )
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Stage not found, is a default stage, or has tasks assigned to it"
        )

