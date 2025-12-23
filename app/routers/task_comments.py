from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.database import get_db
from app.dependencies import get_current_user, get_current_agency
from app.schemas.task_comment import TaskComment, TaskCommentCreate, TaskCommentUpdate
from app import crud

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["task-comments"])

@router.post("/", response_model=TaskComment, status_code=status.HTTP_201_CREATED)
def create_task_comment(
    task_id: UUID,
    comment: TaskCommentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Create a new comment on a task"""
    # Verify task exists and belongs to agency
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud.crud_task_comment.create_task_comment(
        db=db,
        comment=comment,
        task_id=task_id,
        user_id=UUID(current_user["id"])
    )

@router.get("/", response_model=List[TaskComment])
def list_task_comments(
    task_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Get all comments for a task"""
    # Verify task exists and belongs to agency
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud.crud_task_comment.get_task_comments(
        db=db,
        task_id=task_id,
        skip=skip,
        limit=limit
    )

@router.patch("/{comment_id}", response_model=TaskComment)
def update_task_comment(
    task_id: UUID,
    comment_id: UUID,
    comment_update: TaskCommentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Update a comment"""
    # Verify task exists
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    updated_comment = crud.crud_task_comment.update_task_comment(
        db=db,
        comment_id=comment_id,
        task_id=task_id,
        comment_update=comment_update,
        user_id=UUID(current_user["id"])
    )
    
    if not updated_comment:
        raise HTTPException(status_code=404, detail="Comment not found or you don't have permission to update it")
    
    return updated_comment

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_comment(
    task_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Delete a comment"""
    # Verify task exists
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    deleted = crud.crud_task_comment.delete_task_comment(
        db=db,
        comment_id=comment_id,
        task_id=task_id,
        user_id=UUID(current_user["id"])
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found or you don't have permission to delete it")
    
    return None

