from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.task_comment_read import TaskCommentRead
from app.models.task_comment import TaskComment
from app.schemas.task_comment_read import TaskCommentReadCreate

def mark_comment_as_read(
    db: Session,
    comment_id: UUID,
    user_id: UUID,
    user_name: Optional[str] = None
) -> TaskCommentRead:
    """Mark a comment as read by a user"""
    # Check if already read
    existing_read = db.query(TaskCommentRead).filter(
        and_(
            TaskCommentRead.comment_id == comment_id,
            TaskCommentRead.user_id == user_id
        )
    ).first()
    
    if existing_read:
        # Update user_name if provided and not already set
        if user_name and not existing_read.user_name:
            existing_read.user_name = user_name
            db.commit()
            db.refresh(existing_read)
        return existing_read
    
    # Create new read record
    db_read = TaskCommentRead(
        comment_id=comment_id,
        user_id=user_id,
        user_name=user_name
    )
    db.add(db_read)
    db.commit()
    db.refresh(db_read)
    
    return db_read

def mark_all_comments_as_read(
    db: Session,
    task_id: UUID,
    user_id: UUID,
    user_name: Optional[str] = None
) -> int:
    """Mark all comments for a task as read by a user"""
    # Get all comment IDs for this task
    comment_ids = db.query(TaskComment.id).filter(
        TaskComment.task_id == task_id
    ).all()
    
    if not comment_ids:
        return 0
    
    comment_id_list = [c[0] for c in comment_ids]
    
    # Get already read comments
    already_read = db.query(TaskCommentRead).filter(
        and_(
            TaskCommentRead.comment_id.in_(comment_id_list),
            TaskCommentRead.user_id == user_id
        )
    ).all()
    
    already_read_ids = {r.comment_id for r in already_read}
    
    # Update user_name for existing reads if provided and not already set
    if user_name:
        for read_record in already_read:
            if not read_record.user_name:
                read_record.user_name = user_name
        if already_read:
            db.commit()
    
    # Create read records for unread comments
    new_reads = []
    for comment_id in comment_id_list:
        if comment_id not in already_read_ids:
            new_reads.append(TaskCommentRead(
                comment_id=comment_id,
                user_id=user_id,
                user_name=user_name
            ))
    
    if new_reads:
        db.add_all(new_reads)
        db.commit()
    
    return len(new_reads)

def get_unread_comment_count(
    db: Session,
    task_id: UUID,
    user_id: UUID
) -> int:
    """Get count of unread comments for a task by a user"""
    # Get all comments for this task
    all_comments = db.query(TaskComment.id).filter(
        TaskComment.task_id == task_id
    ).all()
    
    if not all_comments:
        return 0
    
    comment_ids = [c[0] for c in all_comments]
    
    # Get read comments
    read_comments = db.query(TaskCommentRead.comment_id).filter(
        and_(
            TaskCommentRead.comment_id.in_(comment_ids),
            TaskCommentRead.user_id == user_id
        )
    ).all()
    
    read_comment_ids = {r[0] for r in read_comments}
    
    # Count unread (comments not in read list)
    unread_count = len(comment_ids) - len(read_comment_ids)
    
    return unread_count

def has_unread_comments(
    db: Session,
    task_id: UUID,
    user_id: UUID
) -> bool:
    """Check if user has unread comments for a task"""
    return get_unread_comment_count(db, task_id, user_id) > 0

