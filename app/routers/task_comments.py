from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import os

from app.database import get_db
from app.dependencies import get_current_user, get_current_agency
from app.schemas.task_comment import TaskComment, TaskCommentCreate, TaskCommentUpdate
from app import crud
from app.services.storage import save_attachment, get_attachment_url

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["task-comments"])

@router.post("/", response_model=TaskComment, status_code=status.HTTP_201_CREATED)
async def create_task_comment(
    task_id: UUID,
    message: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Create a new comment on a task with optional file attachment"""
    # Verify task exists and belongs to agency
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate that at least message or attachment is provided
    if not message and not attachment:
        raise HTTPException(status_code=400, detail="Either message or attachment must be provided")
    
    # Handle file upload if provided
    attachment_url = None
    attachment_name = None
    attachment_type = None
    if attachment and attachment.filename:
        try:
            file_key = save_attachment(attachment, f"task_comments/{task_id}")
            attachment_url = file_key
            attachment_name = attachment.filename
            attachment_type = attachment.content_type or "application/octet-stream"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {str(e)}")
    
    # Create comment data
    comment_data = TaskCommentCreate(
        message=message or "",
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        attachment_type=attachment_type
    )
    
    comment = crud.crud_task_comment.create_task_comment(
        db=db,
        comment=comment_data,
        task_id=task_id,
        user_id=UUID(current_user["id"])
    )
    
    # Generate presigned URL for attachment if exists
    if comment.attachment_url:
        try:
            presigned_url = get_attachment_url(comment.attachment_url, expiration=3600 * 24 * 7)  # 7 days
            if presigned_url:
                # Update the comment object with presigned URL for response
                comment.attachment_url = presigned_url
        except Exception:
            # Fallback to S3 public URL if presigned URL generation fails
            s3_bucket = os.getenv('S3_BUCKET_NAME', '')
            if s3_bucket:
                comment.attachment_url = f"https://{s3_bucket}.s3.amazonaws.com/{comment.attachment_url}"
    
    return comment

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
    
    comments = crud.crud_task_comment.get_task_comments(
        db=db,
        task_id=task_id,
        skip=skip,
        limit=limit
    )
    
    # Generate presigned URLs for attachments
    s3_bucket = os.getenv('S3_BUCKET_NAME', '')
    for comment in comments:
        if comment.attachment_url:
            try:
                presigned_url = get_attachment_url(comment.attachment_url, expiration=3600 * 24 * 7)  # 7 days
                if presigned_url:
                    comment.attachment_url = presigned_url
                elif s3_bucket:
                    comment.attachment_url = f"https://{s3_bucket}.s3.amazonaws.com/{comment.attachment_url}"
            except Exception:
                # Fallback to S3 public URL if presigned URL generation fails
                if s3_bucket:
                    comment.attachment_url = f"https://{s3_bucket}.s3.amazonaws.com/{comment.attachment_url}"
    
    return comments

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

