import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class TaskCollaborator(Base):
    """Many-to-many relationship between tasks and users (collaborators)"""
    __tablename__ = "task_collaborators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    added_by = Column(UUID(as_uuid=True), nullable=True)  # Who added this collaborator
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="collaborators")

    # Ensure unique task-user combination
    __table_args__ = (
        UniqueConstraint('task_id', 'user_id', name='uq_task_collaborator'),
    )

