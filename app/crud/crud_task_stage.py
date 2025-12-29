from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional

from app.models.task_stage import TaskStage
from app.schemas.task_stage import TaskStageCreate, TaskStageUpdate

def create_stage(db: Session, stage: TaskStageCreate, agency_id: UUID, user_id: UUID) -> TaskStage:
    db_stage = TaskStage(
        **stage.model_dump(),
        agency_id=agency_id,
        created_by=user_id
    )
    db.add(db_stage)
    db.commit()
    db.refresh(db_stage)
    return db_stage

def get_stage(db: Session, stage_id: UUID, agency_id: UUID) -> Optional[TaskStage]:
    return db.query(TaskStage).filter(
        and_(TaskStage.id == stage_id, TaskStage.agency_id == agency_id)
    ).first()

def get_stages_by_agency(db: Session, agency_id: UUID) -> List[TaskStage]:
    return db.query(TaskStage).filter(
        TaskStage.agency_id == agency_id
    ).order_by(TaskStage.sort_order.asc(), TaskStage.created_at.asc()).all()

def update_stage(db: Session, stage_id: UUID, stage_update: TaskStageUpdate, agency_id: UUID) -> Optional[TaskStage]:
    db_stage = get_stage(db, stage_id, agency_id)
    if not db_stage:
        return None
    
    update_data = stage_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_stage, field, value)
    
    db.commit()
    db.refresh(db_stage)
    return db_stage

def delete_stage(db: Session, stage_id: UUID, agency_id: UUID, user_id: UUID) -> bool:
    db_stage = get_stage(db, stage_id, agency_id)
    if not db_stage:
        return False
    
    # Don't allow deletion of default stages
    if db_stage.is_default:
        return False
    
    # Check if any tasks are using this stage
    from app.models.task import Task
    tasks_count = db.query(Task).filter(Task.stage_id == stage_id).count()
    if tasks_count > 0:
        return False  # Can't delete stage with tasks
    
    db.delete(db_stage)
    db.commit()
    return True

def initialize_default_stages(db: Session, agency_id: UUID, user_id: UUID) -> List[TaskStage]:
    """Initialize default stages for an agency if they don't exist"""
    existing_stages = get_stages_by_agency(db, agency_id)
    if existing_stages:
        return existing_stages
    
    default_stages = [
        {"name": "To Do", "description": "Tasks that need to be started", "color": "#3b82f6", "sort_order": 0, "is_completed": False, "is_blocked": False},
        {"name": "In Progress", "description": "Tasks currently being worked on", "color": "#f59e0b", "sort_order": 1, "is_completed": False, "is_blocked": False},
        {"name": "Need Review", "description": "Tasks waiting for review", "color": "#8b5cf6", "sort_order": 2, "is_completed": False, "is_blocked": False},
        {"name": "On Hold", "description": "Tasks that are temporarily paused", "color": "#fbbf24", "sort_order": 3, "is_completed": False, "is_blocked": False},
        {"name": "Complete", "description": "Completed tasks", "color": "#10b981", "sort_order": 4, "is_completed": True, "is_blocked": False},
        {"name": "Blocked", "description": "Tasks that are blocked", "color": "#ef4444", "sort_order": 5, "is_completed": False, "is_blocked": True},
    ]
    
    created_stages = []
    for stage_data in default_stages:
        db_stage = TaskStage(
            **stage_data,
            agency_id=agency_id,
            created_by=user_id,
            is_default=True
        )
        db.add(db_stage)
        created_stages.append(db_stage)
    
    db.commit()
    for stage in created_stages:
        db.refresh(stage)
    
    return created_stages

