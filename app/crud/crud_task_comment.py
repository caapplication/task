from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.task_comment import TaskComment
from app.models.activity_log import ActivityLog
from app.schemas.task_comment import TaskCommentCreate, TaskCommentUpdate

def create_task_comment(
    db: Session,
    comment: TaskCommentCreate,
    task_id: UUID,
    user_id: UUID
) -> TaskComment:
    """Create a new comment on a task"""
    db_comment = TaskComment(
        task_id=task_id,
        user_id=user_id,
        message=comment.message
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    # Create activity log for comment
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Comment added",
        details=f"Added a comment: {comment.message[:100]}{'...' if len(comment.message) > 100 else ''}",
        event_type="comment_added",
        to_value={"comment_id": str(db_comment.id), "message_preview": comment.message[:100]}
    )
    db.add(activity_log)
    db.commit()
    
    return db_comment

def get_task_comment(
    db: Session,
    comment_id: UUID,
    task_id: UUID
) -> Optional[TaskComment]:
    """Get a comment by ID"""
    return db.query(TaskComment).filter(
        and_(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id
        )
    ).first()

def get_task_comments(
    db: Session,
    task_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[TaskComment]:
    """Get all comments for a task"""
    return db.query(TaskComment).filter(
        TaskComment.task_id == task_id
    ).order_by(TaskComment.created_at.asc()).offset(skip).limit(limit).all()

def update_task_comment(
    db: Session,
    comment_id: UUID,
    task_id: UUID,
    comment_update: TaskCommentUpdate,
    user_id: UUID
) -> Optional[TaskComment]:
    """Update a comment (only by the user who created it)"""
    db_comment = get_task_comment(db, comment_id, task_id)
    if not db_comment:
        return None
    
    # Only allow the creator to update their comment
    if db_comment.user_id != user_id:
        return None
    
    old_message = db_comment.message
    if comment_update.message is not None:
        db_comment.message = comment_update.message
        db_comment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_comment)
    
    # Create activity log for comment update
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Comment updated",
        details=f"Updated a comment",
        event_type="comment_updated",
        from_value={"comment_id": str(comment_id), "old_message": old_message[:100]},
        to_value={"comment_id": str(comment_id), "new_message": comment_update.message[:100] if comment_update.message else None}
    )
    db.add(activity_log)
    db.commit()
    
    return db_comment

def delete_task_comment(
    db: Session,
    comment_id: UUID,
    task_id: UUID,
    user_id: UUID
) -> bool:
    """Delete a comment (only by the user who created it or admin)"""
    db_comment = get_task_comment(db, comment_id, task_id)
    if not db_comment:
        return False
    
    # Only allow the creator to delete their comment
    if db_comment.user_id != user_id:
        return False
    
    # Create activity log before deletion
    activity_log = ActivityLog(
        task_id=task_id,
        user_id=user_id,
        action="Comment deleted",
        details=f"Deleted a comment",
        event_type="comment_deleted",
        from_value={"comment_id": str(comment_id), "message": db_comment.message[:100]}
    )
    db.add(activity_log)
    
    db.delete(db_comment)
    db.commit()
    return True

