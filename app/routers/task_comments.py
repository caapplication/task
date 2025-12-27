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
from app.crud import crud_task_comment_read

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
    
    # Allow empty messages - no validation required
    # Users can send messages with or without text/attachments
    
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
    
    # Emit real-time event for new comment
    try:
        from app.socketio_manager import emit_new_comment, emit_unread_update
        import asyncio
        
        # Prepare comment data for emission
        comment_dict = {
            "id": str(comment.id),
            "task_id": str(comment.task_id),
            "user_id": str(comment.user_id),
            "message": comment.message,
            "attachment_url": comment.attachment_url,
            "attachment_name": comment.attachment_name,
            "attachment_type": comment.attachment_type,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }
        
        sender_user_id = str(current_user["id"])
        
        # Emit to all users watching this task (except sender)
        asyncio.create_task(emit_new_comment(str(task_id), comment_dict, sender_user_id))
        
        # Update unread status for all users in the task (except sender)
        # Get all users who should see this task (assigned, collaborators, etc.)
        from app.crud import crud_task
        task_obj = crud_task.get_task(db, task_id, current_agency["id"])
        if task_obj:
            users_to_notify = set()
            if task_obj.assigned_to:
                users_to_notify.add(str(task_obj.assigned_to))
            if task_obj.created_by:
                users_to_notify.add(str(task_obj.created_by))
            
            # Get collaborators
            from app.crud import crud_task_collaborator
            collaborators = crud_task_collaborator.get_task_collaborators(db, task_id)
            for collab in collaborators:
                users_to_notify.add(str(collab.user_id))
            
            # Remove sender from notification list
            users_to_notify.discard(sender_user_id)
            
            # Emit unread update to all relevant users
            for user_id in users_to_notify:
                asyncio.create_task(emit_unread_update(str(task_id), user_id, True))
    except Exception as e:
        # Don't fail the request if Socket.IO fails
        print(f"Socket.IO emission error: {e}")
    
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
    """Get all comments for a task and mark them as read for the current user"""
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
    
    # Mark all comments as read for the current user when they view the chat
    user_id = UUID(current_user["id"])
    # Store user name for display
    user_name = current_user.get("name") or current_user.get("email") or None
    
    # Get all comments for this task before marking as read
    from app.models.task_comment import TaskComment
    from app.models.task_comment_read import TaskCommentRead
    from sqlalchemy import and_
    from datetime import datetime, timezone
    
    comment_ids = db.query(TaskComment.id).filter(
        TaskComment.task_id == task_id
    ).all()
    comment_id_list = [c[0] for c in comment_ids]
    
    # Get already read comment IDs before marking
    already_read = db.query(TaskCommentRead.comment_id).filter(
        and_(
            TaskCommentRead.comment_id.in_(comment_id_list),
            TaskCommentRead.user_id == user_id
        )
    ).all()
    already_read_ids = {r[0] for r in already_read}
    
    # Mark all comments as read
    new_reads_count = crud_task_comment_read.mark_all_comments_as_read(db, task_id, user_id, user_name)
    
    # Emit read receipt updates for all newly read comments
    if new_reads_count > 0:
        try:
            from app.socketio_manager import emit_comment_read_receipt
            import asyncio
            
            # Get the comment IDs that were newly marked as read
            newly_marked_ids = [cid for cid in comment_id_list if cid not in already_read_ids]
            
            # Get the read receipts for newly marked comments (already committed in mark_all_comments_as_read)
            recent_reads = db.query(TaskCommentRead).filter(
                and_(
                    TaskCommentRead.comment_id.in_(newly_marked_ids),
                    TaskCommentRead.user_id == user_id
                )
            ).all()
            
            # Emit read receipt for each newly marked comment
            for read_receipt in recent_reads:
                receipt_data = {
                    "id": str(read_receipt.id),
                    "user_id": str(read_receipt.user_id),
                    "read_at": read_receipt.read_at.isoformat() if read_receipt.read_at else None,
                    "user_name": read_receipt.user_name or user_name or "Unknown",
                    "user_email": current_user.get("email") or "N/A"
                }
                asyncio.create_task(emit_comment_read_receipt(
                    str(task_id), 
                    str(read_receipt.comment_id), 
                    receipt_data
                ))
        except Exception as e:
            # Don't fail the request if Socket.IO fails
            print(f"Socket.IO read receipt emission error: {e}")
    
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

@router.get("/{comment_id}/reads", response_model=List[dict])
def get_comment_read_receipts(
    task_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_agency: dict = Depends(get_current_agency),
):
    """Get list of users who have read a specific comment"""
    # Verify task exists
    from app import crud as crud_module
    task = crud_module.crud_task.get_task(db, task_id, current_agency["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify comment exists and belongs to task
    comment = crud.crud_task_comment.get_task_comment(db, comment_id, task_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Get all read receipts for this comment
    from app.models.task_comment_read import TaskCommentRead
    
    read_receipts = db.query(TaskCommentRead).filter(
        TaskCommentRead.comment_id == comment_id
    ).order_by(TaskCommentRead.read_at.desc()).all()
    
    # Build response using stored user_name, fallback to fetching if needed
    from app.routers.tasks import fetch_user_info_from_login_service
    import os
    token_str = os.getenv("INTERNAL_SERVICE_TOKEN", None)
    
    receipts_with_user_info = []
    for receipt in read_receipts:
        # user_name field stores user name
        user_name = receipt.user_name or "Unknown"
        user_email = "N/A"
        user_role = "N/A"
        
        # Only fetch from login service if name is not stored
        if not receipt.user_name:
            try:
                user_info = fetch_user_info_from_login_service(receipt.user_id, token_str)
                if user_info:
                    user_name = user_info.get("name") or user_info.get("email") or "Unknown"
                    user_email = user_info.get("email") or "N/A"
                    user_role = user_info.get("role") or "N/A"
                    # Update the stored name for future use
                    receipt.user_name = user_name
                    db.commit()
            except Exception as e:
                # If we can't fetch user info, use defaults
                print(f"Error fetching user info for {receipt.user_id}: {e}")
        
        receipts_with_user_info.append({
            "id": str(receipt.id),
            "user_id": str(receipt.user_id),
            "read_at": receipt.read_at.isoformat() if receipt.read_at else None,
            "user_name": user_name,
            "user_email": user_email,
            "user_role": user_role
        })
    
    return receipts_with_user_info

